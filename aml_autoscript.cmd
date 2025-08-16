# This script will only be loaded once

setenv bootcmd 'echo '**********run auto boot cmd**********'; run autobootcmd'

# autobootcmd:
# echo 'try boot from emmc'
# run try_emmc_bootcmd
# echo 'try boot from usb drive'
# if usb start; then
# 	run try_usbdrive_bootcmd
# fi
# echo 'fallback to vendor boot'
# run storeboot

setenv autobootcmd 'echo 'try boot from emmc'; run try_emmc_bootcmd; echo 'try boot from usb drive'; if usb start; then run try_usbdrive_bootcmd; fi; echo 'fallback to vendor boot'; run storeboot'

setenv try_emmc_bootcmd 'if fatload mmc 1 1020000 boot.scr; then setenv devtype mmc; setenv devnum 1; autoscr 1020000; fi'

setenv try_usbdrive_bootcmd 'for usbdevnum in 0 1 2 3; do if fatload usb ${usbdevnum} 1020000 boot.scr; then setenv devtype usb; setenv devnum $usbdevnum; autoscr 1020000; fi; done'

setenv upgrade_step 2

saveenv
echo "U-Boot env is set successfully, restart after 3 seconds!"
reboot

# Restore to default env:
# setenv bootcmd 'run storeboot'
# setenv upgrade_step 2
# env delete autobootcmd
# env delete try_emmc_bootcmd
# env delete try_usbdrive_bootcmd
# saveenv
# reboot

# Recompile with:
# mkimage -C none -A arm -T script -d /boot/aml_autoscript.cmd /boot/aml_autoscript
