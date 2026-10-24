#!/bin/bash
cd "$(dirname "$0")" || exit 1
if ! bash install.sh; then
 printf '\nSetup did not finish. Review the message above. Press Return to close.\n'
 read -r reply
 exit 1
fi
