from __future__ import with_statement

"""
Requires phantomjs 2.0
"""

from selenium import webdriver
from selenium.common import exceptions
from time import sleep

import signal
from contextlib import contextmanager
class TimeoutException(Exception): pass
@contextmanager
def time_limit(seconds):
    def signal_handler(signum, frame):
        raise TimeoutException("Timed out!")
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)


class LoginException(Exception):
    """ 
    Raise when we are unable to log into alarm.com
    """
    pass


class SystemArmedError(Exception):
    """
    Raise when the system is already armed and an attempt
    to arm it again is made.
    """
    pass


class SystemDisarmedError(Exception):
    """
    Raise when the system is already disamred and an attempt
    to disarm the system is made.
    """
    pass


class Alarmdotcom(object):
    """
    Access to alarm.com partners and accounts.

    This class is used to interface with the options available through
    alarm.com. The basic functions of checking system status and arming
    and disarming the system are possible.
    """

    # Page elements on alarm.com that are needed
    # Using a dict for the attributes to set whether it is a name or id for locating the field
    LOGIN_URL = 'https://www.alarm.com/login?m=no_session&ReturnUrl=/web/Security/SystemSummary.aspx'
    LOGIN_USERNAME = ('name', 'ctl00$ContentPlaceHolder1$loginform$txtUserName')
    LOGIN_PASSWORD = ('name', 'txtPassword')
    LOGIN_BUTTON = ('name', 'ctl00$ContentPlaceHolder1$loginform$signInButton')

    STATUS_IMG = ('id', 'ctl00_phBody_ArmingStateWidget_imgState')
    
    BTN_DISARM = ('id', 'ctl00_phBody_ArmingStateWidget_btnDisarm')
    BTN_ARM_STAY = ('id', 'ctl00_phBody_ArmingStateWidget_btnArmStay', 'ctl00_phBody_ArmingStateWidget_btnArmOptionStay')
    BTN_ARM_AWAY = ('id', 'ctl00_phBody_ArmingStateWidget_btnArmAway', 'ctl00_phBody_ArmingStateWidget_btnArmOptionStay')

    # Image to check if hidden or not while the system performs it's action.
    STATUS_UPDATING = {'id': 'ctl00_phBody_ArmingStateWidget_imgArmingUpdating'}
    
    def __init__(self, username, password):
        """
        Open a selenium connection.
 
        This uses the PhantomJS library with selenium. We will attempt to keep the
        connection alive but if we need to reconnect we will.
        """
        self._driver = webdriver.PhantomJS()
        self.username = username
        self.password = password
        if not self._login():
            raise LoginException('Unable to login to alarm.com')

    def _login(self):
        """
        Login to alarm.com
        """
        # Attempt to login to alarm.com
        self._driver.get(self.LOGIN_URL)
  
        # Check the login title to make sure it is the right one.
        if self._driver.title == 'Customer Login':

            user = self._driver.find_element(by=self.LOGIN_USERNAME[0], value=self.LOGIN_USERNAME[1])
            pwd = self._driver.find_element(by=self.LOGIN_PASSWORD[0], value=self.LOGIN_PASSWORD[1])
            btn = self._driver.find_element(by=self.LOGIN_BUTTON[0], value=self.LOGIN_BUTTON[1])

            user.send_keys(self.username)
            pwd.send_keys(self.password)
            btn.click() 
           
            if self._driver.title == 'Current System Status':
                return True
            else:
                return False
        else:
            return False

    def _set_state(self, btn, timeout=10):
        """
        Wait for the status to complete it's update.
        """
        button = self._driver.find_element(by=btn[0], value=btn[1])
        button.click()
        sleep(1)

        if len(btn) > 2:
            button_option = self._driver.find_element(by=btn[0], value=btn[2])
            button_option.click()

            # Loop until the system updates the status
            try:
                with time_limit(timeout):
                    try:
                        self._driver.find_element(by='id', value='ctl00_phBody_ArmingStateWidget_imgPopupSpinner')
                    except exceptions.NoSuchElementException:
                        pass
            except TimeoutException:
                pass

    @property
    def state(self):
        """
        Check the current status of the alarm system.
        """
        # Click the refresh button to verify the state if it was made somewhere else
        self._driver.find_element(by='id', value='ctl00_phBody_ArmingStateWidget_btnArmingRefresh').click()

        # Wait a second for the widget to refresh
        sleep(1)

        # Recheck the current status
        current_status = self._driver.find_element(by=self.STATUS_IMG[0],
                                                   value=self.STATUS_IMG[1]).get_attribute('alt')

        return current_status

    def disarm(self):
        """
        Disarm the alarm system
        """
        if self.state != 'Disarmed':
            self._set_state(self.BTN_DISARM)
        else:
            raise SystemDisarmedError('The system is already disarmed!')

    def arm_away(self):
        """
        Arm the system in away mode.
        """
        if self.state == 'Disarmed':
            self._set_state(self.BTN_ARM_AWAY)
        else:
            raise SystemArmedError('The system is already armed!')

    def arm_stay(self):
        """
        Arm the system in stay mode.
        """
        if self.state == 'Disarmed':
            self._set_state(self.BTN_ARM_STAY)
        else:
            raise SystemArmedError('The system is already armed!')