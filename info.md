A Home Assistant integration for your Reolink security NVR/cameras. It enables you to detect motion, control IR lights, recording, and sending emails.

*Configuration guide can be found [here](https://github.com/JimStar/reolink_cctv/blob/master/README.md).*


{% if installed %}

{% if version_installed == version_available  %}
*You already have the latest released version installed.*
{% else %}
#### Changes of version {{ version_available }}

- Fixed a bug in `reolink-ip` lib caused by wrong parameter description in Reolink API "guide". The "Siren" switch was affected by this.
- Some code refactoring/optimizations in `reolink-ip` lib.

**IMPORTANT**: Version **0.1.X** has different camera IDs in comparison to **0.0.X**, so you probably will need to re-config all places where camera-streams are referenced.
{% endif %}

{% endif %}
