#!/bin/bash
choco pack
choco apikey -k $chocoapikey -source https://push.chocolatey.org/
choco push $chocopkg -s https://push.chocolatey.org/