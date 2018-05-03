import logging
import time
import json

try:
    from urllib.parse import urlencode, urlunsplit
except ImportError:
    from urlparse import urlunsplit
    from urllib import urlencode

    import requests
    from bs4 import BeautifulSoup

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.WARN)

"""
  Most of the information below is from the User Manual at:
    https://static.lennox.com/pdfs/owners/s30/Lennox_iComfortS30_Homeowner_Manual.pdf
  The heirachy of constructs in the Lennox Page looks like this:
    There may be one or more Homes,
    Which may contain one or more Lennox Climate Control Systems,
    Which may contain one or more Zones.

    Zones
      Each Zone contains a Mode, which is one of:
        (Off, Cool Only, Heat Only, Heat/Cool)
        Each of these Modes contain required Temperatures, as:
          (Off = None,
           Cool = Max Indoor Temp; >= Cooling Starts,
           Heat = Min Indoor Temp <= Heating Starts,
           Heat/Cool = Max and Min as above.  As a note, these cannot be closer
             than 3 degrees from each other.
      Addtionally, each zone contains a Fan setting:
        On = Fan is turned on regardless of Climate Control,
        Auto = Fan is controlled by Climate Control,
        Circulate = As Auto, and also runs at a low rate between CC cycles.  The
        amount of time circulate runs per hour can be configured from the
        Settings->Fan->Circulate option (9 to 27 minutes).
        Allergen Defender = Circulates air inside when the air quality is bad
          outside to filter it.  This is basically Circulate mode that only runs
          if the Air Quality outside is poor.  For this to be an available
          option, Allergen Defender must be enabled in the Settings->Fan menu
          under Allergen Defender.
      
      Schedules
            The Mode and Fan settings can be automatically adjusted
        based on one or more Schedules.  These schedules change based on the
        season: Summer, Winter, and Spring/Fall. 
            Each schedule is subdivided into Periods.  Each Period has a start
        time, as well as Mode and Fan settings.  Schedules can be configured
        to have the same Periods for all days of the week, different Periods
        for weekdays and weekends, or a different set of Periods every day.  For
        each configured day, there may be at most 4 periods.
        
            Schedule IQ has the same periods every day, and is based  wake-up
        time, sleep time, and away Mode scheduling rather than season or day
        of the week.

      Current Set Points (Mode)
        Instantaneous changes can be made to Mode, Temperatures, and Fan.  These
        will be automatically changed when the next schedule changes them, or
        a "Schedule Hold" can be set for a fixed amount of time to prevent the
        schedule from changing them.  The changes and the hold can be cancelled
        by disabling the Schedule Hold.

      Away Mode
        This mode may be set per household, and configures the Thermostat to
        put all LCCs and Zones into a cost-saving Heat/Cool setting.  The
        temperature for these may be controlled from the Settings->Away menu
        under away-set-points. You may also toggle Smart Away on, which uses
        the installed iComfort App on your phone to control automatic enabling
        of the Away feature using Geofencing for all participating devices.

  For all requests, look for a 302 redirect, with the location:
     /Account/Login?_isSessionExpired=True
  This means we need to log in again, so set login = false, and clear the data.
  TODO: We should also parse and check if a login fails, and we are locked out.
  This should yield a different error so the user understands no amount of
  uname/password changes will fix this issue (for 15 minutes).
"""
class IComfort3Zone(object):
    UPDATE_REFERER_PATH = 'Dashboard/HomeDetails' 
    DETAILS_PATH = 'Dashboard/RefreshLatestZoneDetailByIndex'

    def __init__(self, home_id, lcc_id, zone_id):
        # static, pre-configured entries
        self.home_id = home_id
        self.lcc_id = lcc_id
        self.zone_id = zone_id

    def __send_update_request(self, session):
        details_referer_query = ( ('zoneId', self.zone_id),
                                  ('homeId', self.home_id),
                                  ('lcc_Id', self.lcc_id),
                                  ('refreshZonedeail', 'False') )
        referer_url = IComfort3Session.create_url(DETAILS_PATH,
                                                  self.details_referer_query)  
        current_millis = (int(time.time()) * 1000), + random.randint(0, 999)
        details_query = ( ('zoneId', self.zone_id), ('isPolling', 'true'),
                          ('lccId', self.lcc_id), ('_', str(current_millis)) )
        update_url = IComfort3Session.create_url(UPDATE_REFERER_PATH,
                                                 details_referer_query)
        update = session.request_json(update_url, referer_url)
        return update


    # The requestor validated that the session has not Failed
    def __parse_update(self, update):
        if not update['Code'] == 'LCC_ONLINE':
            return False
        flat = dict((k,v) for k,v in update['data']['zoneDetail']
        # Ambient temp comes across not flattened, and as a string
        flat['AmbientTemperature'] = int(flat['AmbientTemperature']['Value'])
        flat['CoolSetPoint'] = flat['CoolSetPoint']['Value']
        flat['HeatSetPoint'] = flat['HeatSetPoint']['Value']
        flat['SingleSetPoint'] = flat['SingleSetPoint']['Value']
        # Done with zone detail now - pop
        update.pop['data']['zonepaging']
        # Copy the rest of data
    
        # Flatten temp entries
        self.HomeName = update['data']['HomeName']
        self.centralMode = update['data']['centralMode']
        self.isSysteminAwayMode = update['data']['isSysteminAwayMode']
        self.sysNotificationCount = update['data']['sysNotificationCount']
        self.systemName = update['data']['systemName']       
        if self.sysNotificationCount:
            __update_notifications(
        self.zoneDetail = update['data']['zoneDetail']


    def fetch_update(self, session):
        """ Fetches an update from the web API.

        Uses the session to fetch the latest status info from the web API for a 
        thermostat, and returns the resulting dictionary.  If there is a problem
        an exception will be thrown.

        Args:
            session: A logged-in session with permission to access this zone.

        Returns:
            A dict with the current status information for this zone.

        Raises:
            Possible Errors
            Username/Password could be wrong
            the session could not be logged in
            The session is now expired
            The system is not currently accessible
        """
        update_json = __send_update_request(session)
        if not update_json:
            return False
        return __parse_update(update_json)

    # FIXME: Do we want getters/setters for each variable?
    def fetch_home_name(self, session):
        update = self.fetch_update(session)
        return update['data']['HomeName']


    #
    def fetch_notifications(self, session):
        return []   
