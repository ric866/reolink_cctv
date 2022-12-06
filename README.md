<h2 align="center">
  <a href="https://reolink.com"><img src="./logo.png" width="200"></a>
  <br>
  <i>Home Assistant Reolink NVR/cameras custom integration</i>
  <br>
</h2>

<p align="center">
  <a href="https://github.com/custom-components/hacs"><img src="https://img.shields.io/badge/HACS-Custom-orange.svg"></a>
  <img src="https://img.shields.io/github/v/release/JimStar/reolink_cctv?display_name=tag&include_prereleases&sort=semver" alt="Current version">
</p>

The `reolink_cctv` implementation allows you to integrate your [Reolink](https://www.reolink.com/) devices (NVR/cameras) in Home Assistant.

## Most important changes/improvements

Improvements in comparison to the `reolink_dev`:
- Implemented Reolink NVRs support. If you've connected to NVR - you'll have just **one** integration entry for that NVR instead of one for each camera. In this case all cameras/sensors/switches are childs of one NVR entry, no mess between NVR-name/camera-names anymore. I think it should work for multichannel-cameras too, but I did not test it.
- Fixed the reason of random command-requests failures, which in `reolink_dev` lead to random warnings/errors in the log from time to time.
- Fixed all the component's mess with its Actions/Triggers/Conditions/Services.
- Fixed the often-happened "Unavailable" status of detection sensors.
- Improved stability of connection with as less polling as possible. **Watchdog-timer** now checks for the session to be alive, and tries to restore if not. It tries to poll only if this still failed.
- The indication-logic this component now follows:  
If ONVIF subscription failed for some reason (ONVIF on the device disabled, port blocked by firewall, etc) - its detection sensors will intentionally show the state "Unavailable": for you to be able to see (without reading the log-file) that there is some problem with ONVIF subscription that needs to be fixed. But despite the sensors' "Unavailable" state, the **watchdog-timer** (after trying to restore the ONVIF subscription every time) polls (only if restoring of subscription failed) for possible motion with the time-interval set up in integration's config. Every time some motion gets detected by watchdog polling - it will switch the sensor(s) to "Detected" state. But as soon as the motion finishes (by next polling), the sensors will get back to "Unavailable" (instead of "Clear"), to continue indicating the ONVIF subscription problem.  
- Workaround for Reolink issue in some camera models/firmwares: because of this issue motion-sensors were not resetting back on such camera models.  
Now if you have such cameras and experience motion-sensors not coming back to "Clear" for a long time - you can tune the "Motion sensor force-off timeout" in integration's config to the desired value. If you have cameras that work OK without this workaround - having this value as "0" would save some HA computing resources.
- Last-record sensor (former "last event") now stores the very last motion event's screenshot **automatically**. It is renamed to "last record" because not always it points to a last *motion event*. For example it can be just a very last **recorded chunk** which in case of continuous 24/7 record stores one-two hours of continuous video, with an "event" start like an hour-two ago (when the chunk's record started). Thus it looks more logical to me if it's named "last record".
- Implemented the `last_record_url` attribute in the last-record sensor, and the "external IP/domain" plus "external port" settings for the camera/NVR (set up in the integration entry's config, not used if empty). Usable if you set up an automation to send a motion-notification to your phone with a video-link in it.  
For example, you can set up different external HTTPS ports in each camera-entry settings, and forward all these external ports in your router to each of your camera (or simply forward the NVR's port if you use NVR-connection). This way, if you for example set the "external IP/domain" in the integration-entry settings like `<some IP>` and the "external port" as `<some port>`, then the generated video link in the `last_record_url` attribute would be like `https://<some IP>:<some port>/cgi-bin/<the rest of the URL>`. The automation could be e.g. like this:  
```
automation:
  - alias: Notify mobile app
    trigger:
      ...
    action:
      - service: notify.mobile_app_<your_device_id_here>
        data:
          message: "Motion event"
          data:
            image: "https://github.com/home-assistant/assets/blob/master/logo/logo.png?raw=true"
            video: "{{ state_attr('sensor.front_left_last_record', 'last_record_url') }}"
```  
**BE CAREFUL THOUGH** with this link: Reolink API requires login/pass credentials provided in a link to be able to watch a video from a device. Thus if you use this functionality - be sure the link is sent over **encrypted** channels, and the link itself is an **HTTPS** link (so that the credentials are not visible to anyone when the link is used).
- Implemented the support of doorbell-cameras: a "**Visitor**" sensor is now available for such cameras. The sensor will trigger when a "Visitor" ONVIF-notification is sent by such camera.
- Implemented a "Face detection" sensor. I see this "Face" AI-detection type sent in these above-mentioned rich ONVIF notifications, so maybe some Reolink cameras have this feature, or will have in future... Thus I've just made use of this AI detection type too in this component.
- Media-browser support for NVRs is implemented.  
I intentionally do not fill-in **all** the thumbnails during media-browsing: this way if your NVR is recording 24/7 - you have the way to distinguish. Those 1-2 hours chunks **with** thumbnails on them had some movement events, and those **without** thumbnails did not have any movements during all chunk recording (so the last-record sensor did not auto-write any thumbnails because no events happened).
- Implemented garbage-collection for old thumbnails/scrennshots when browsing, to not overfill Home Assistant drive. But you still **need to setup a periodic action** that calls the integration's `cleanup_thumbnails` service: it will cleanup all the motion-events thumbnails older than the "Playback range" config setting (10 days by default). Otherwise you could overfill your HA drive by hi-res thumbnails, especially if you have a lot of motion-events on a lot of cameras.
- The device **actions** now allow to create a screenshot-file for a particular camera at a current time, stored as `snapshot.jpg` instead of a name representing the time of the beginning of a last **recorded** video-chunk (used for thumbnails previously, which now is done automaticlly by a "last record" sensor). Not sure though this custom-action is needed at all - because there is already a standard HA screenshot-making service for any camera (just a little bit clunkier to setup)...
- When opening a current camera-stream sometimes the hi-res RTMP/RTSP video stream is too laggy. So there is a new "**images**" option introduced in stream-types config, which will just show a choppy image sequence instead of video stream (which is faster).
- Now the **rich** ONVIF subscription format is supported: I've found out that some Reolink cameras send the notification messages that already have all the information about kind of AI object detected. Thus, if receiving such a rich notification, this component does not need to start a long communication with NVR/camera to ask it what particular object was just detected, before reporting motion - it just uses this info directly from the received notification message, which is much faster and doesn't waste machine/network resources.
- Reolink's data-normalisation of NVR/camera API-commands is a mess (same as their "API reference" document found in their site downloads). To still have it a little more clear "what is global - what is camera-specific", switches are split in two sets in integration-entry UI: *kinda* global ones, and camera-specific ones (useful if NVR connection is used).

## IMPORTANT notes

I tested this component with Home assistant **2022.8.6**. Not sure if it would work with a lot older one...

:warning: This new component most likely will **conflict** if used at the same time with `reolink_dev`. So it would be a good idea to save the Home Assistant config folder, and remove `reolink_dev` before start using this one. Maybe you'll need to make few corrections to already existing camera-automations, because there are some differences in this component's namings/actions...

:warning: **There is a BUG in Reolink NVR firmware** (at least I tested it on my **RLN8-410**): it only sends ONVIF events-notifications if motion happened on the camera connected to its **very first** (index "0") channel. Reolink is aware of that, and told me they are "working on it"...  
Still works kinda OK for me, because all my cameras share a little part of view with the channel-0 camera - so when channel-0 sees something and sends an ONVIF event, the component anyway polls all cameras "what's happening?" and reports movements from **all** cameras if any...  
If this is not the case for you - maybe it would make sense to continue bombing Reolink support with complaints about that, forcing them to finally fix this silly bug... Because other than that - I like it a lot more to have a connection to NVR than having a couple of separate integration-entries for each camera separately. Especially that there are no recordings of NVR's big hard-drive available from HA if connected to a camera instead of the NVR...

**Another weird thing** with Reolink firmware: the 8-channels **RLN8-410** NVR reports itself as having **12** channels. So don't be surprised if you got provided with a selection list of 12 channels during its initial setup.

:warning: The code is rewritten quite significantly, so there is a good chance some bugs could still happen. I did not test **direct** camera connections so far (I have it connected to my **RLN8-410** NVR). So if you get any bugs when connecting to cameras directly - feel free to open tickets in a tracker here...

**There is NO LOGO** on this integration inside Home Assistant. HA devs for some reason made logos as **external links** to their `brands` repo site, instead of allowing to custom-components to supply logo-file **locally** with some `manifest.json` config. And they **rejected** to accept my simple pull-request to their `brands` repo before the custom-component repo becomes available to users. Which introduces stupid chicken-egg problem, where I must release an ugly-looking custom-component without a logo before I even allowed to do a pull-request with logo-files to their `brands` repo...  
I suspect **all** components will have no logos shown up with this approach if HA is in local network and all external access is blocked for it for some security reasons... E.g. for a reason that any external HA-image request from your IP is a "knuck-knuck" to a "big brother" reporting "there is a Home Assistant at this address, with this list of integrations activated"...  
I have no desire nor time to argue with them, so it is how it is. This component works excellently for me and all my cameras, and I don't care how it looks with this stupid "*not available*" external-link logo...

## Installation

### Manual install

```bash
# Download a copy of this repository
$ wget https://github.com/JimStar/reolink_cctv/archive/master.tar.gz

# Unzip the archive
$ tar -xzf master.tar.gz

# Move the reolink_cctv directory into your custom_components directory in your Home Assistant install
$ mv reolink_cctv-master/custom_components/reolink_cctv <home-assistant-install-directory>/config/custom_components/

# Clean up
rm -rf ./reolink_cctv-master
rm -f ./master.tar.gz
```

### HACS install ([How to install HACS](https://hacs.xyz/docs/setup/prerequisites))

  1. Click on HACS in the Home Assistant menu
  2. Click on **Integrations**
  3. Click the top right menu (the three dots)
  4. Select **Custom repositories**
  5. Paste the repository URL (`https://github.com/JimStar/reolink_cctv`) in the dialog box
  6. Select category **Integration**
  7. Click **Add**
  8. Click **Install** on the **Reolink IP NVR/camera** box that has now appeared


> :warning: **After executing one of the above installation methods, restart Home Assistant. Also clear your browser cache before proceeding to the next step, as the integration may not be visible otherwise.**


In your Home Assistant installation go to: **Configuration > Integrations**, click the button **Add Integration > Reolink IP NVR/camera**
Enter the details for your NVR/camera. The device and other sensors will now be available as an entity.

For the motion detection to work, Home Assistant must be reachable via http from your local network. So when using https internally, motion detection will not work at this moment.

For the services and switch entities of this integration to work, you need a camera user of type "Administrator". Users of type "Guest" can only view the switch states but cannot change them and cannot call the services. Users are created and managed through the web interface of the camera (Device Settings / Cog icon -> User) or through the app (Device Settings / Cog icon -> Advanced -> User Management).

If you connected **directly to NVR** (instead of to each camera separately):
- Reolink NVR firmware has a critical **BUG**: the ONVIF SWN motion detection notifications are sent by NVR only if motion is detected on a camera connected to its very first channel (with the index 0). So Home Assistant will not inform you about any motion events happening on other NVR channels.
Reolink told me they are "aware of this bug and working on it", but it looks to me they always reply with this same phrase to any bug reported to them... Would be useful if every user would be reporting this same bug to Reolink again and again, pushing on them to finally fix this...

### Troubleshooting
* Make sure you have set up the **Internal URL** in Home Assistant to the correct IP address and port (do not use the mDNS name)
* Make sure ONVIF is enabled on your camera/NVR. It might be disabled by default and can only be enabled when you have a screen connected to the NVR, not via webb or app clients. Be aware that this can be reset during a firmware upgrade.

## Services

The Reolink integration supports all default camera [services](https://www.home-assistant.io/integrations/camera/#services) and additionally provides the following services:

### Service `reolink_cctv.cleanup_thumbnails`

Set the day and night mode parameter of the camera.

| Service data attribute  | Optional  | Description  |
| :---------------------- | :-------- | :----------- |
| `older_than`            | no        | Remove all thumbnails older than the specified date, irregardless of matching VoD.

### Service `reolink_cctv.set_sensitivity`

Set the motion detection sensitivity of the camera. Either all time schedule presets can be set at once, or a specific preset can be specified.

| Service data attribute  | Optional  | Description  |
| :---------------------- | :-------- | :----------- |
| `entity_id`             | no        | The camera to control.
| `sensitivity`           | no        | The sensitivity to set, a value between 1 (low sensitivity) and 50 (high sensitivity).
| `preset`                | yes       | The time schedule preset to set. Presets can be found in the Web UI of the camera.

### Service `reolink_cctv.set_backlight`

Optimizing brightness and contrast levels to compensate for differences between dark and bright objects using either BLC or WDR mode.
This may improve image clarity in high contrast situations, but it should be tested at different times of the day and night to ensure there is no negative effect.

| Service data attribute  | Optional  | Description  |
| :---------------------- | :-------- | :----------- |
| `entity_id`             | no        | The camera to control.
| `mode`                  | no        | The backlight parameter supports the following values: `BACKLIGHTCONTROL`: use Backlight Control `DYNAMICRANGECONTROL`: use Dynamic Range Control `OFF`: no optimization

### Service `reolink_cctv.set_daynight`

Set the day and night mode parameter of the camera.

| Service data attribute  | Optional  | Description  |
| :---------------------- | :-------- | :----------- |
| `entity_id`             | no        | The camera to control.
| `mode`                  | no        | The day and night mode parameter supports the following values: `AUTO` Auto switch between black & white mode `COLOR` Always record videos in color mode `BLACKANDWHITE` Always record videos in black & white mode.

### Service `reolink_cctv.ptz_control`

Control the PTZ (Pan Tilt Zoom) movement of the camera.

| Service data attribute  | Optional  | Description  |
| :---------------------- | :-------- | :----------- |
| `entity_id`             | no        | The camera to control.
| `command`               | no        | The command to execute. Possibe values are: `AUTO`, `DOWN`, `FOCUSDEC`, `FOCUSINC`, `LEFT`, `LEFTDOWN`, `LEFTUP`, `RIGHT`, `RIGHTDOWN`, `RIGHTUP`, `STOP`, `TOPOS`, `UP`, `ZOOMDEC` and `ZOOMINC`.
| `preset`                | yes       | In case of the command `TOPOS`, pass the preset ID here. The possible presets are listed as attribute on the camera.
| `speed`                 | yes       | The speed at which the camera moves. Not applicable for the commands: `STOP` and `AUTO`.

**The camera keeps moving until the `STOP` command is passed to the service.**

## Camera

This integration creates a camera entity, providing a live-stream configurable from the integrations page. In the options menu, the following parameters can be configured:

| Parameter               | Description                                                                                                 |
| :-------------------    | :---------------------------------------------------------------------------------------------------------- |
| Stream                  | Switch between Sub or Main camera stream.                                                                   |
| Protocol                | Switch between the RTMP or RTSP streaming protocol, or "images" to watch series of still images instead.    |

## Binary Sensor

When the camera supports motion detection events, a binary sensor is created for real-time motion detection. The time to switch motion detection off can be configured via the options menu, located at the integrations page. Please notice: for using the motion detection, your Home Assistant should be reachable (within you local network) over http (not https).

| Parameter               | Description                                                                                                 |
| :-------------------    | :---------------------------------------------------------------------------------------------------------- |
| Motion sensor off delay | Control how many seconds it takes (after the last motion detection) for the binary sensor to switch off.    |

When the camera supports AI objects detection, a binary sensor is created for each type of object (person, vehicle, pet)

## Switch

Depending on the camera, the following switches are created:

| Switch               | Description |
| :------------------- | :------------------------------------------------------------ |
| Email                | Switch email alerts from the camera when motion is detected.  |
| FTP                  | Switch FTP upload of photo and video when motion is detected. |
| IR lights            | Switch the infrared lights to auto or off.                    |
| Record audio         | Record auto or mute. This also implies the live-stream.       |
| Push notifications   | Enable or disable push notifications to Android/IOS.          |
| Recording            | Switch recording to the SD card or hard drive.                |

## Unsupported models

The following models are not to be supported:

- Battery-powered cameras
- B800: Only with NVR
- B400: Only with NVR
- D400: Only with NVR
- Lumus
