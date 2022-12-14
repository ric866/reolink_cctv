A Home Assistant integration for your Reolink security NVR/cameras. It enables you to detect motion, control IR lights, recording, and sending emails.

*Configuration guide can be found [here](https://github.com/JimStar/reolink_cctv/blob/master/README.md).*


{% if installed %}

{% if version_installed == version_available  %}
*You already have the latest released version installed.*
{% else %}
#### Changes of version {{ version_available }}

- Bug fix in the `reolink-ip` lib.

**IMPORTANT**: Version **0.1.X** has different camera IDs, so you probably will need to re-config all places where camera-streams are referenced.
{% endif %}

{% endif %}
