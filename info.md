A Home Assistant integration for your Reolink security NVR/cameras. It enables you to detect motion, control IR lights, recording, and sending emails.

*Configuration guide can be found [here](https://github.com/JimStar/reolink_cctv/blob/master/README.md).*


{% if installed %}

#### Changes from version {{ version_installed }}

{% if version_installed == version_available  %}
*You already have the latest released version installed.*
{% endif %}

{% if version_installed.replace("v", "") | float < 0.0.34  %}
- Fixed a regression in `reolink-ip` lib, related to **0.0.33** improvements.
{% endif %}
{% if version_installed.replace("v", "") | float < 0.0.33  %}
- Implemented the support of channels' auto-population for multi-channel devices. No need to select the channels anymore when adding a new integration-entry.  
You still need to restart HA after connecting/disconnecting cameras to/from your NVR, for the integration to see the changes.
- Implemented the automatic enabling of ONVIF on the device in case it is disabled.
- Minor fixes...
{% endif %}
{% if version_installed.replace("v", "") | float < 0.0.32  %}
- More changes in spotlight-switch state synchronization.
{% endif %}
{% if version_installed.replace("v", "") | float < 0.0.31  %}
- Improvements in spotlight-switch state synchronization.
{% endif %}
{% if version_installed.replace("v", "") | float < 0.0.30  %}
- More fixes of spotlight switching functionality in the `reolink-ip` lib.
{% endif %}
{% if version_installed.replace("v", "") | float < 0.0.29  %}
- Few fixes of spotlight switching functionality in the `reolink-ip` lib.
{% endif %}
{% if version_installed.replace("v", "") | float < 0.0.28  %}
- Fixed a bug: snapshots still recorded when "last record" sensor was disabled.
- Implemented the "Visit device" link in the device card to allow to visit the NVR/camera for configuration or diagnostics.
- Minor improvements in `reolink-ip` library.
{% endif %}
{% if version_installed.replace("v", "") | float < 0.0.27  %}
- Few stability and error-logging improvements...
{% endif %}
{% if version_installed.replace("v", "") | float < 0.0.26  %}
- Improvements in `reolink-ip` library: workaround for Reolink Logout command bug that affects some camera models.  
Be prepared that after some sudden power failure or HA crash, your Reolink device may not allow the component to login before the previous session expires (might take even an hour). So the component's initialization in HA might keep failing during all this period, with HA logging errors from time to time...
- Fixed an error logged if some AI-sensor gets disabled.
{% endif %}
{% if version_installed.replace("v", "") | float < 0.0.25  %}
- Fixed a regression bug, introduced with new features in **0.0.24**.
{% endif %}
{% if version_installed.replace("v", "") | float < 0.0.24  %}
- Implemented doorbell-cameras support: visitor sensor is now available for such cameras. The sensor will trigger when a "Visitor" ONVIF-notification is sent by a camera.
- Changed the "Playback range" setting to be in **days** instead of in months. This allows more precise control over amount of storage spent on a drive for all the thumbnails of all cameras' motion events. Please re-check this setting after updating to **0.0.24**. And don't forget to setup a periodic action that calls `cleanup_thumbnails` service of this integration.  
You probably need to refresh/clear the browser's cache to update the changes in config-window fields.
- Fixed issue with integration's webhook/event IDs being not human-readable.
{% endif %}
{% if version_installed.replace("v", "") | float < 0.0.23  %}
- Bug fix: folder names for thumbnails' storage were different in some cases.
{% endif %}
{% if version_installed.replace("v", "") | float < 0.0.22  %}
- Fixed binary sensor bug.
- Implemented the "external port" setting for `last_record_url` links (in addition to "external URL"): to be able to map different ports in the router to the same local ports on cameras.
{% endif %}
{% if version_installed.replace("v", "") | float < 0.0.21  %}
- Improved/simplified the `cleanup_thumbnails` service: now it just always uses the entry's "Playback range (months)" setting and deletes all thumbnails older than that.  
The previous "Older than" attribute did not make sense, as it was just a particular static date instead of a period.
{% endif %}
{% if version_installed.replace("v", "") | float < 0.0.20  %}
- Quick fix release.
{% endif %}
{% if version_installed.replace("v", "") | float < 0.0.19  %}
- Improved the `last_record_url` attribute in last-record sensor. Now it doesn't use RTMP stream (HTTP/HTTPS links instead), and can use the "external URL" for the camera/NVR (set up in the entry's config, not used if empty).
{% endif %}
{% if version_installed.replace("v", "") | float < 0.0.18  %}
- Implemented the `last_record_url` attribute in last-record sensor.
{% endif %}
{% if version_installed.replace("v", "") | float < 0.0.17  %}
- Fixed email switch bug.
{% endif %}
{% if version_installed.replace("v", "") | float < 0.0.15  %}
- Improvements of session handling, both in the component and in `reolink-ip` lib.
{% endif %}
{% if version_installed.replace("v", "") | float < 0.0.14  %}
- Bug fixes in `reolink-ip` lib.
{% endif %}
{% if version_installed.replace("v", "") | float < 0.0.13  %}
- Bug fixes in `reolink-ip` lib.
- Test-workaround for a Reolink login-bug in some cameras.
{% endif %}
{% if version_installed.replace("v", "") | float < 0.0.12  %}
- Bug fixes in both, the component and `reolink-ip` lib.
{% endif %}
{% if version_installed.replace("v", "") | float < 0.0.11  %}
- Improved workaround for Reolink issue in some camera models, where motion-sensors may not reset back to "Clear":  
Now the "motion off delay" is split in two separate settings: usual "off **delay**" (prolong delay of motion-on state) and "force-off **timeout**" (force-switch the sensor back to "Clear" after a timeout).  
**Clear the browser's cache** if you don't see the name of this new input field in options dialog.
{% endif %}
{% if version_installed.replace("v", "") | float < 0.0.10  %}
- Bug fixes...
{% endif %}
{% if version_installed.replace("v", "") | float < 0.0.8  %}
- Fixed device-login regression bug (introduced in **0.0.7**): max-sessions limit was reached in some cases. Integration in **0.0.7** could not work normally in this case.
- Workaround for Reolink issue in some camera models (like E1 for example): because of this issue motion-sensors were not resetting back on such cameras.  
Now if you have such cameras and experience motion-sensors not coming back to "Clear" for a long time - you can tune the "Motion sensor off delay" in integration's config to the desired value. If you have cameras that work OK without this workaround - having this value as "0" would save some HA computing resources.
- Minor fixes...
{% endif %}
{% if version_installed.replace("v", "") | float < 0.0.7  %}
- Fixed subscription renewal bug.
- Workaround for episodic initial login-fail seen in a log.
- Minor efficiency improvements...
{% endif %}
{% if version_installed.replace("v", "") | float < 0.0.6  %}
- Polished the indication-logic this component now follows:  
If ONVIF subscription failed for some reason (ONVIF on the device disabled, port blocked by firewall, etc) - its detection sensors will intentionally show the state "Unavailable": for you to be able to see (without reading the log-file) that there is some problem with ONVIF subscription that needs to be fixed. But despite the sensors' "Unavailable" state, the **watchdog-timer** (after trying to restore the ONVIF subscription every time) polls (only if restoring of subscription failed) for possible motion with the time-interval set up in integration's config. Every time some motion gets detected by watchdog polling - it will switch the sensor(s) to "Detected" state. But as soon as the motion finishes (by next polling), the sensors will get back to "Unavailable" (instead of "Clear"), to continue indicating the ONVIF subscription problem.  
Feel free to [let me know](https://github.com/JimStar/reolink_cctv/discussions) if you would have any arguments *against* this logic...
{% endif %}
{% if version_installed.replace("v", "") | float < 0.0.5  %}
- Bug fixes...
{% endif %}

{% endif %}
