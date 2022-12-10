A Home Assistant integration for your Reolink security NVR/cameras. It enables you to detect motion, control IR lights, recording, and sending emails.

*Configuration guide can be found [here](https://github.com/JimStar/reolink_cctv/blob/master/README.md).*


{% if installed %}

{% if version_installed == version_available  %}
*You already have the latest released version installed.*
{% else %}
#### Changes of version {{ version_available }}

- Stream compression format option removed (deprecated by Reolink).
- Now few cameras are created for each channel: one for each stream type. All but "Sub" are disabled by default.
{% endif %}

{% endif %}
