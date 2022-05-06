"""Etekcity/Valceno Smart Light Bulbs."""

import logging
import json
import colorsys
from collections import namedtuple
from typing import Union, Dict
from abc import ABCMeta, abstractmethod
from pyvesync.helpers import Helpers as helpers
from pyvesync.vesyncbasedevice import VeSyncBaseDevice


logger = logging.getLogger(__name__)


# Possible features - dimmable, color_temp, rgb_shift
feature_dict: dict = {
    'ESL100':
        {
            'module': 'VeSyncBulbESL100',
            'features': ['dimmable']
        },
    'ESL100CW':
        {
            'module': 'VeSyncBulbESL100CW',
            'features': ['dimmable', 'color_temp']
        },
    'XYD0001':
        {
            'module': 'VeSyncBulbValcenoA19MC',
            'features': ['dimmable', 'color_temp', 'rgb_shift']
        }
}


bulb_modules: dict = {k: v['module'] for k, v in feature_dict.items()}

__all__: list = list(bulb_modules.values()) + ['bulb_modules']


def pct_to_kelvin(pct: float, max_k: int = 6500, min_k: int = 2700) -> float:
    """Convert percent to kelvin."""
    kelvin = ((max_k - min_k) * pct / 100) + min_k
    return kelvin


class VeSyncBulb(VeSyncBaseDevice):
    """Base class for VeSync Bulbs."""

    __metaclass__ = ABCMeta

    def __init__(self, details: Dict[str, Union[str, list]],
                 manager):
        """Initialize VeSync smart bulb base class."""
        super().__init__(details, manager)
        self._brightness = 0
        self._color_temp = 0
        self._color_value = 0
        self._color_hue = 0
        self._color_saturation = 0
        self._color_mode = ''   # possible: white, color, hsv
        self.features = feature_dict.get(self.device_type, {}).get('features')
        if self.features is None:
            logger.error("No configuration set for - %s", self.device_name)
            raise Exception

    @property
    def brightness(self) -> int:
        """Return brightness of vesync bulb."""
        if self.dimmable_feature and self._brightness is not None:
            return self._brightness
        return 0

    @property
    def color_temp_kelvin(self) -> int:
        """Return white color temperature of bulb in Kelvin."""
        if self.color_temp_feature and self._color_temp is not None:
            return int(pct_to_kelvin(self._color_temp))
        return 0

    @property
    def color_temp_pct(self) -> int:
        """Return white color temperature of bulb in percent."""
        if self.color_temp_feature and self._color_temp is not None:
            return int(self._color_temp)
        return 0

    @property
    def color_hue(self) -> float:
        """Return color hue of bulb.""" # from 0 to 360
        if self.rgb_shift_feature and self._color_hue is not None:
            return float(self._color_hue)
        return 0

    @property
    def color_saturation(self) -> float:
        """Return color saturation of bulb in percent.""" # from 0 to 100
        if self.rgb_shift_feature and self._color_saturation is not None:
            return float(self._color_saturation)
        return 0

    @property
    def color_value(self) -> int: 
        """Return color value of bulb in percent.""" # from 0 to 100
        if self.rgb_shift_feature and self._color_value is not None:
            return int(self._color_value)
        return 0

    @property
    def color_value_hsv(self) -> tuple:
        """Return color of bulb in hsv."""
        if self.rgb_shift_feature and self._color_value is not None:
            hsv = namedtuple('hsv',['hue','saturation','value'])
            hsv_tuple = hsv(hue = float(round(self._color_hue,2)),
                            saturation = float(round(self._color_saturation,2)),
                            value = int(round(self._color_value,0))
                            )
            # hsv = (float(self._color_hue) , float(self._color_saturation), int(self._color_value))
            return hsv_tuple
        return 0

    @property
    def color_value_rgb(self) -> tuple:
        """Return color of bulb in rgb."""
        if self.rgb_shift_feature and self._color_value is not None:
            rgb = namedtuple('rgb',['red','green','blue'])
            converted = colorsys.hsv_to_rgb(self._color_hue/360, self._color_saturation/100, self._color_value/100)
            #rgb_tuple = tuple( [round(x*255,2) for x in rgb] )
            rgb_tuple = rgb(red = float(round(converted[0],2)),
                            green = float(round(converted[1],2)),
                            blue = float(round(converted[2],2))
                            )
            return rgb_tuple
        return 0

    @property
    def color_mode(self) -> str:
        """Return color mode of bulb.""" # { white, hsv }
        if self.rgb_shift_feature and self._color_mode is not None:
            return str(self._color_mode)
        return None

    @property
    def dimmable_feature(self) -> bool:
        """Return true if dimmable bulb."""
        if 'dimmable' in self.features:
            return True
        return False

    @property
    def color_temp_feature(self) -> bool:
        """Return true if bulb supports white color temperature changes."""
        if 'color_temp' in self.features:
            return True
        return False

    @property
    def rgb_shift_feature(self) -> bool:
        """Return True if bulb supports changing color (RGB)."""
        if 'rgb_shift' in self.features:
            return True
        return False

    @abstractmethod
    def get_details(self) -> None:
        """Get vesync bulb details."""
        
    @abstractmethod
    def interpret_apicall_result(self) -> None:
        """Update bulb status from any api call response."""

    @abstractmethod
    def toggle(self, status: str) -> bool:
        """Toggle vesync lightbulb."""

    @abstractmethod
    def get_config(self) -> None:
        """Call api to get configuration details and firmware."""

    def turn_on(self) -> bool:
        """Turn on vesync bulbs."""
        if self.toggle('on'):
            self.device_status = 'on'
            return True
        logger.warning('Error turning %s on', self.device_name)
        return False

    def turn_off(self) -> bool:
        """Turn off vesync bulbs."""
        if self.toggle('off'):
            self.device_status = 'off'
            return True
        logger.warning('Error turning %s off', self.device_name)
        return False

    def update(self) -> None:
        """Update bulb details."""
        self.get_details()

    def display(self) -> None:
        """Return formatted bulb info to stdout."""
        super().display()
        if self.connection_status == 'online':
            disp = [] # initiate list
            if self.dimmable_feature:
                disp.append( ('Brightness: ', self.brightness, '%') )
            if self.color_temp_feature:
                disp.append( ('White Temperature Pct: ', self.color_temp_pct, '%') )
                disp.append( ('White Temperature Kelvin: ', self.color_temp_kelvin, 'K') )
            if self.rgb_shift_feature:
                disp.append( ('ColorHSV: ', str(self.color_value_hsv), '') )
                disp.append( ('ColorRGB: ', str(self.color_value_rgb), '') )
                disp.append( ('ColorMode: ', self.color_mode, '') )
            if len(disp) > 0:
                for line in disp:
                    print(f'{line[0]:.<30} {line[1]} {line[2]}')

    def displayJSON(self) -> str:
        """Return bulb device info in JSON format."""
        sup = super().displayJSON()
        sup_val = json.loads(sup)
        if self.connection_status == 'online':
            if self.dimmable_feature:
                sup_val.update({'Brightness': str(self.brightness)})
            if self.color_temp_feature:
                sup_val.update({'WhiteTemperaturePct': str(self.color_temp_pct)})
                sup_val.update({'WhiteTemperatureKelvin': str(self.color_temp_kelvin)})
            if self.rgb_shift_feature:
                sup_val.update({'ColorHSV': str(self.color_value_hsv)})
                sup_val.update({'ColorRGB': str(self.color_value_rgb)})
                sup_val.update({'ColorMode': str(self.color_mode)})
        return json.dumps(sup_val, indent = 4)


class VeSyncBulbESL100(VeSyncBulb):
    """Object to hold VeSync ESL100 light bulb."""

    def __init__(self, details, manager):
        """Initialize Etekcity ESL100 Dimmable Bulb."""
        super().__init__(details, manager)
        self.details: dict = {}

    def get_details(self) -> None:
        """Get details of dimmable bulb."""
        body = helpers.req_body(self.manager, 'devicedetail')
        body['uuid'] = self.uuid
        r, _ = helpers.call_api(
            '/SmartBulb/v1/device/devicedetail',
            'post',
            headers=helpers.req_headers(self.manager),
            json_object=body,
        )
        if helpers.code_check(r):
            self.connection_status = r.get('connectionStatus')
            self.device_status = r.get('deviceStatus')
            if self.dimmable_feature:
                self._brightness = int(r.get('brightNess'))
        else:
            logger.debug('Error getting %s details', self.device_name)

    def get_config(self) -> None:
        """Get configuration of dimmable bulb."""
        body = helpers.req_body(self.manager, 'devicedetail')
        body['method'] = 'configurations'
        body['uuid'] = self.uuid

        r, _ = helpers.call_api(
            '/SmartBulb/v1/device/configurations',
            'post',
            headers=helpers.req_headers(self.manager),
            json_object=body,
        )

        if helpers.code_check(r):
            self.config = helpers.build_config_dict(r)
        else:
            logger.warning('Error getting %s config info', self.device_name)

    def toggle(self, status) -> bool:
        """Toggle dimmable bulb."""
        body = helpers.req_body(self.manager, 'devicestatus')
        body['uuid'] = self.uuid
        body['status'] = status
        r, _ = helpers.call_api(
            '/SmartBulb/v1/device/devicestatus',
            'put',
            headers=helpers.req_headers(self.manager),
            json_object=body,
        )
        if helpers.code_check(r):
            self.device_status = status
            return True
        return False

    def set_brightness(self, brightness: int) -> bool:
        """Set brightness of dimmable bulb."""
        if not self.dimmable_feature:
            logger.debug('%s is not dimmable', self.device_name)
            return False
        if isinstance(brightness, int) and (brightness <= 0 or brightness > 100):
            logger.warning('Warning: brightness value should be between 0 and 100')
        # ensure brightness is between 0 and 100
        brightness = max(0,(min(100,brightness)))
        body = helpers.req_body(self.manager, 'devicestatus')
        body['uuid'] = self.uuid
        body['status'] = 'on'
        body['brightNess'] = str(brightness)
        r, _ = helpers.call_api(
            '/SmartBulb/v1/device/updateBrightness',
            'put',
            headers=helpers.req_headers(self.manager),
            json_object=body,
        )

        if helpers.code_check(r):
            self._brightness = brightness
            return True

        logger.debug('Error setting brightness for %s', self.device_name)
        return False


class VeSyncBulbESL100CW(VeSyncBulb):
    """VeSync Tunable and Dimmable White Bulb."""

    def __init__(self, details, manager):
        """Initialize Etekcity Tunable white bulb."""
        super().__init__(details, manager)

    def get_details(self) -> None:
        """Get details of tunable bulb."""
        body = helpers.req_body(self.manager, 'bypass')
        body['cid'] = self.cid
        body['jsonCmd'] = {'getLightStatus': 'get'}
        body['configModule'] = self.config_module
        r, _ = helpers.call_api(
            '/cloud/v1/deviceManaged/bypass',
            'post',
            headers=helpers.req_headers(self.manager),
            json_object=body,
        )
        if not isinstance(r, dict) or not helpers.code_check(r):
            logger.debug('Error calling %s', self.device_name)
            return
        response = r
        if response.get('result', {}).get('light') is not None:
            light = response.get('result', {}).get('light')
            self.connection_status = 'online'
            self.device_status = light.get('action', 'off')
            if self.dimmable_feature:
                self._brightness = light.get('brightness')
            if self.color_temp_feature:
                self._color_temp = light.get('colorTempe')
        elif response.get('code') == -11300027:
            logger.debug('%s device offline', self.device_name)
            self.connection_status = 'offline'
            self.device_status = 'off'
        else:
            logger.debug(
                '%s - Unknown return code - %d with message %s',
                self.device_name,
                response.get('code'),
                response.get('msg'),
            )

    def get_config(self) -> None:
        """Get configuration and firmware info of tunable bulb."""
        body = helpers.req_body(self.manager, 'bypass_config')
        body['uuid'] = self.uuid

        r, _ = helpers.call_api(
            '/cloud/v1/deviceManaged/configurations',
            'post',
            headers=helpers.req_headers(self.manager),
            json_object=body,
        )

        if helpers.code_check(r):
            self.config = helpers.build_config_dict(r)
        else:
            logger.debug('Error getting %s config info', self.device_name)

    def toggle(self, status) -> bool:
        """Toggle tunable bulb."""
        body = helpers.req_body(self.manager, 'bypass')
        body['cid'] = self.cid
        body['configModule'] = self.config_module
        body['jsonCmd'] = {'light': {'action': status}}
        r, _ = helpers.call_api(
            '/cloud/v1/deviceManaged/bypass',
            'post',
            headers=helpers.req_headers(self.manager),
            json_object=body,
        )
        if helpers.code_check(r) == 0:
            self.device_status = status
            return True
        logger.debug('%s offline', self.device_name)
        self.device_status = 'off'
        self.connection_status = 'offline'
        return False

    def set_brightness(self, brightness: int) -> bool:
        """Set brightness of tunable bulb."""
        if not self.dimmable_feature:
            logger.debug('%s is not dimmable', self.device_name)
            return False
        if brightness <= 0 or brightness > 100:
            logger.debug('Invalid brightness')
            return False

        body = helpers.req_body(self.manager, 'bypass')
        body['cid'] = self.cid
        body['configModule'] = self.config_module
        if self.device_status == 'off':
            light_dict = {'action': 'on', 'brightness': brightness}
        else:
            light_dict = {'brightness': brightness}
        body['jsonCmd'] = {'light': light_dict}
        r, _ = helpers.call_api(
            '/cloud/v1/deviceManaged/bypass',
            'post',
            headers=helpers.req_headers(self.manager),
            json_object=body,
        )

        if helpers.code_check(r):
            self._brightness = brightness
            return True
        self.device_status = 'off'
        self.connection_status = 'offline'
        logger.debug('%s offline', self.device_name)

        return False

    def set_color_temp(self, color_temp: int) -> bool:
        """Set Color Temperature of Bulb in pct (1 - 100)."""
        if color_temp < 0 or color_temp > 100:
            logger.debug('Invalid color temperature - only between 0 and 100')
            return False
        body = helpers.req_body(self.manager, 'bypass')
        body['cid'] = self.cid
        body['jsonCmd'] = {'light': {}}
        if self.device_status == 'off':
            light_dict = {'action': 'on', 'colorTempe': color_temp}
        else:
            light_dict = {'colorTempe': color_temp}
        body['jsonCmd']['light'] = light_dict
        r, _ = helpers.call_api(
            '/cloud/v1/deviceManaged/bypass',
            'post',
            headers=helpers.req_headers(self.manager),
            json_object=body,
        )

        if not helpers.code_check(r):
            return False

        if r.get('code') == -11300027:
            logger.debug('%s device offline', self.device_name)
            self.connection_status = 'offline'
            self.device_status = 'off'
            return False
        if r.get('code') == 0:
            self.device_status = 'on'
            self._color_temp = color_temp
            return True
        logger.debug(
            '%s - Unknown return code - %d with message %s',
            self.device_name,
            r.get('code'),
            r.get('msg'),
        )
        return False


class VeSyncBulbValcenoA19MC(VeSyncBulb):
    """VeSync Multicolor Bulb."""

    def __init__(self, details, manager):
        """Initialize Valceno Multicolor bulb."""
        super().__init__(details, manager)

    def get_details(self) -> None:
        """Get details of multicolor bulb."""
        body = helpers.req_body(self.manager, 'bypassV2')
        # body = helpers.bypass_body_v2(self.manager)
        body['cid'] = self.cid
        body['configModule'] = self.config_module
        body['payload'] = {
            'method': 'getLightStatusV2',
            'source': 'APP',
            'data': {}
        }
        r, _ = helpers.call_api(
            '/cloud/v2/deviceManaged/bypassV2',
            'post',
            headers=helpers.req_header_bypass(),
            json_object=body,
        )
        if not isinstance(r, dict) or not helpers.code_check(r):
            logger.debug('Error calling %s', self.device_name)
            return
        self.interpret_apicall_result(r)

    def interpret_apicall_result(self, response) -> None:
        if response.get('result', {}).get('result') is not None:
            innerresult = response.get('result', {}).get('result')
            self.connection_status = 'online'
            self.device_status = innerresult.get('enabled', 'off')
            if self.dimmable_feature:
                self._brightness = innerresult.get('brightness')
            if self.color_temp_feature:
                self._color_temp = innerresult.get('colorTemp')
            if self.rgb_shift_feature:
                self._color_mode = innerresult.get('colorMode')
                self._color_hue = round(innerresult.get('hue')/27.777777,2)
                self._color_saturation = innerresult.get('saturation')/100
                self._color_value = innerresult.get('value')
        elif response.get('code') == -11300030:
            logger.debug('%s device request timeout', self.device_name)
            self.connection_status = 'offline'
            self.device_status = 'off'
        elif response.get('code') == -11300027:
            logger.debug('%s device offline', self.device_name)
            self.connection_status = 'offline'
            self.device_status = 'off'
        else:
            logger.debug(
                '%s - Unknown return code - %d with message %s',
                self.device_name,
                response.get('code'),
                response.get('msg'),
            )

    def get_config(self) -> None:
        """Get configuration and firmware info of multicolor bulb."""
        body = helpers.req_body(self.manager, 'devicedetail')
        body['method'] = 'configurations'
        body['uuid'] = self.uuid
        r, _ = helpers.call_api(
            '/cloud/v1/deviceManaged/configurations',
            'post',
            headers=helpers.req_header_bypass(),
            json_object=body,
        )
        if helpers.code_check(r):
            self.config = helpers.build_config_dict(r)
        else:
            logger.debug('Error getting %s config info', self.device_name)
            logger.debug('  return code - %d with message %s',r.get('code'), r.get('msg'))

    def toggle(self, status) -> bool:
        """Toggle multicolor bulb."""
        body = helpers.req_body(self.manager, 'bypassV2')
        if status == 'off':
           statusBool = False
        else:
           statusBool = True
        body['cid'] = self.cid
        body['configModule'] = self.config_module
        body['payload'] = {
            'method': 'setSwitch',
            'source': 'APP',
            'data': {
                'id': 0,
                'enabled': statusBool
                }
            }
        r, _ = helpers.call_api(
            '/cloud/v2/deviceManaged/bypassV2',
            'post',
            headers=helpers.req_header_bypass(),
            json_object=body)
        if helpers.code_check(r):
            self.device_status = status
            return True
        logger.debug('%s offline', self.device_name)
        self.device_status = 'off'
        self.connection_status = 'offline'
        return False

    def set_brightness(self, brightness: int) -> bool:
        """Set brightness of multicolor bulb."""
        if not self.dimmable_feature:
            logger.debug('%s is not dimmable', self.device_name)
            return False
        if brightness <= 0 or brightness > 100:
            logger.warning('Warning: brightness value should be between 0 and 100')
        # ensure brightness is between 0 and 100
        brightness = max(0,(min(100,brightness)))
        body = helpers.req_body(self.manager, 'bypassV2')
        body['cid'] = self.cid
        body['configModule'] = self.config_module
        body['payload'] = {
            'method': 'setLightStatusV2',
            'source': 'APP',
            'data': {
                'force': 0,
                'brightness': brightness,
                'colorTemp': '',
                'colorMode': '',
                'hue': '',
                'saturation': '',
                'value': ''
                }
            }
        r, _ = helpers.call_api(
            '/cloud/v2/deviceManaged/bypassV2',
            'post',
            headers=helpers.req_header_bypass(),
            json_object=body
            )
        if helpers.code_check(r):
            self.interpret_apicall_result(r)
            self._brightness = brightness
            return True
        self.device_status = 'off'
        self.connection_status = 'offline'
        logger.debug('%s offline', self.device_name)
        return False

    def set_color_temp(self, color_temp: int) -> bool:
        """Set White Temperature of Bulb in pct (1 - 100)."""
        if not self.color_temp_feature:
            logger.debug('%s is not white temperature tunable', self.device_name)
            return False
        if color_temp <= 0 or color_temp > 100:
            logger.debug('Warning: color_temp value should be between 0 and 100')
        color_temp = max(0,(min(100,color_temp))) # ensure color_temp is between 0 and 100
        body = helpers.req_body(self.manager, 'bypassV2')
        body['cid'] = self.cid
        body['configModule'] = self.config_module
        body['payload'] = {
            'method': 'setLightStatusV2',
            'source': 'APP',
            'data': {
                'force': 1,
                'brightness': '',
                'colorTemp': color_temp,
                'colorMode': 'white',
                'hue': '',
                'saturation': '',
                'value': ''
                }
            }
        r, _ = helpers.call_api(
            '/cloud/v2/deviceManaged/bypassV2',
            'post',
            headers=helpers.req_header_bypass(),
            json_object=body,
            )
        if helpers.code_check(r):
            self.interpret_apicall_result(r)
            self.device_status = 'on'
            self._color_temp = color_temp
            return True
        self.device_status = 'off'
        self.connection_status = 'offline'
        logger.debug('%s offline', self.device_name)
        return False
            

    def set_color_saturation(self, color_saturation: int) -> bool:
        """Set Color Saturation of Bulb in pct (1 - 100)."""
        if not self.color_temp_feature:
            logger.debug('%s is not color capable', self.device_name)
            return False
        if color_saturation <= 0 or color_saturation > 100:
            logger.debug('Warning: color_saturation value should be between 0 and 100')
        color_saturation = max(0,(min(100,color_saturation))) # ensure color_temp is between 0 and 100
        color_saturation_api : int = round(color_saturation*100, None) # convert value to api expected range (0-10000)
        body = helpers.req_body(self.manager, 'bypassV2')
        body['cid'] = self.cid
        body['configModule'] = self.config_module
        body['payload'] = {
            'method': 'setLightStatusV2',
            'source': 'APP',
            'data': {
                'force': 1,
                'brightness': '',
                'colorTemp': '',
                'colorMode': 'hsv',
                'hue': '',
                'saturation': color_saturation_api,
                'value': ''
                }
            }
        r, _ = helpers.call_api(
            '/cloud/v2/deviceManaged/bypassV2',
            'post',
            headers=helpers.req_header_bypass(),
            json_object=body,
            )
        if helpers.code_check(r):
            self.interpret_apicall_result(r)
            self.device_status = 'on'
            self._color_saturation = color_saturation
            return True
        self.device_status = 'off'
        self.connection_status = 'offline'
        logger.debug('%s offline', self.device_name)
        return False

    def set_color_hue(self, color_hue: float) -> bool:
        """Set Color Hue of Bulb (0 - 360)."""
        if not self.rgb_shift_feature:
            logger.debug('%s is not color capable', self.device_name)
            return False
        if color_hue <= 0 or color_hue > 360:
            logger.warning('Warning: color_hue value should be between 0 and 360')
        # ensure color_hue is between 0 and 360
        color_hue = max(0,(min(360,color_hue)))
        # convert value to api expected range (0-10000)
        color_hue_api : int = round(color_hue*27.777777,None)
        body = helpers.req_body(self.manager, 'bypassV2')
        body['cid'] = self.cid
        body['configModule'] = self.config_module
        body['payload'] = {
            'method': 'setLightStatusV2',
            'source': 'APP',
            'data': {
                'force': 1,
                'brightness': '',
                'colorTemp': '',
                'colorMode': 'hsv',
                'hue': color_hue_api,
                'saturation': '',
                'value': ''
                }
            }
        r, _ = helpers.call_api(
            '/cloud/v2/deviceManaged/bypassV2',
            'post',
            headers=helpers.req_header_bypass(),
            json_object=body
            )
        if helpers.code_check(r):
            self.interpret_apicall_result(r)
            self.device_status = 'on'
            self._color_hue = color_hue
            return True
        self.device_status = 'off'
        self.connection_status = 'offline'
        logger.debug('%s offline', self.device_name)
        return False


    def set_color_mode(self, color_mode: str) -> bool:
        """Set Color Mode of Bulb (white / hsv)."""
        if not self.rgb_shift_feature:
            logger.debug('%s is not color capable', self.device_name)
            return False
        color_mode = color_mode.lower()
        possible_modes = {'white': 'white',
                          'color': 'hsv',
                          'hsv': 'hsv'}
        if not color_mode in possible_modes.keys():
          logger.error("Color mode specified is not acceptable")
          return False
        body = helpers.req_body(self.manager, 'bypassV2')
        body['cid'] = self.cid
        body['configModule'] = self.config_module
        body['payload'] = {
            'method': 'setLightStatusV2',
            'source': 'APP',
            'data': {
                'force': 1,
                'brightness': '',
                'colorTemp': '',
                'colorMode': possible_modes[color_mode],
                'hue': '',
                'saturation': '',
                'value': ''
                }
            }
        r, _ = helpers.call_api(
            '/cloud/v2/deviceManaged/bypassV2',
            'post',
            headers=helpers.req_header_bypass(),
            json_object=body
            )
        if helpers.code_check(r):
            self.interpret_apicall_result(r)
            self.device_status = 'on'
            self._color_mode = possible_modes[color_mode]
            return True
        self.device_status = 'off'
        self.connection_status = 'offline'
        logger.debug('%s offline', self.device_name)
        return False
