---
name: Bug report
about: 'Create a report to help us improve.'
title: ''
labels: ''
assignees: ''

---

**Describe the bug**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior.

**Expected behavior**
A clear and concise description of what you expected to happen.

**Debug log would be very helpful**
If applicable, switch on debug-logging, and attach here a full log-file: from the HA restart, and covering the time where the issue happened.  
```
logger:
  default: warning
  logs:
    custom_components.reolink_cctv: debug
    reolink_ip: debug
```

**Screenshots**
If applicable, add screenshots to help explain your problem.

**Environment:**
Please provide useful information about your environment, like:
 - Home Assistant version
 - Reolink NVR/camera model
 - NVR/camera firmware

**Additional context**
Maybe any other context about the problem here.
