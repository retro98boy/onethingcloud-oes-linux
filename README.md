# 固件

[Armbian](https://github.com/retro98boy/armbian-build)

# 硬件

![hw-version](pictures/hw-version.jpg)

eMMC短接点：

![emmc-short](pictures/emmc-short.jpg)

调试串口：

![debug-uart](pictures/debug-uart.jpg)

# 安全启动

在设备上电log中存在：

```
[1.244567 Inits done]
secure task start!
high task start!
low task start!
run into bl31
NOTICE:  BL31: v1.3(release):30bb4ac
NOTICE:  BL31: Built : 18:30:34, Nov 27 2020
NOTICE:  BL31: G12A secure boot!
NOTICE:  BL31: BL33 decompress pass
ERROR:   Error initializing runtime service opteed_fast
```

其中`NOTICE:  BL31: G12A secure boot!`说明该设备开启了安全启动。这意味着SoC在上电后会拒绝运行未经签名的镜像

幸运的是该设备有原厂USB刷写包流出，可以用于救机。刷写包中的SECURE_BOOT_SET和DDR_ENC.USB非常重要。前者是SoC的efuse镜像，虽说厂家在设备出厂时已经OTP过了，但是不知为什么使用Amlogic USB Burning Tool刷写时还是需要它。后者是厂家提供的签名/加密过的FIP，包含ddrfw BL2 BL31 BL33（U-Boot）

USB刷写包中还包括DDR.USB，这是未签名/加密的FIP，对该设备最大的意义是DDR驱动。如果给设备换了未开启安全启动的SoC，就可以参考[此处](https://github.com/retro98boy/cainiao-cniot-core-linux)制作带主线U-Boot的FIP来引导内核，自由度更高，应该可以直接从SATA硬盘引导内核。或者有厂家的密钥流出，我们也能对自制FIP进行签名使用

从[此处](https://github.com/khadas/u-boot/blob/khadas-vim3-p-64bit/fip/g12b/build.sh)可以得出加密/签名的命令：

```bash
# 根据aml-user-key.sig生成efuse镜像，即SECURE_BOOT_SET
aml_encrypt_g12b --efsgen --amluserkey aml-user-key.sig --output u-boot.bin.encrypt.efuse --level v3
# 使用aml-user-key.sig签名FIP
aml_encrypt_g12b --bootsig --input u-boot.bin --amluserkey aml-user-key.sig --aeskey enable --output u-boot.bin.encrypt --level v3
# 使用aml-user-key.sig签名Android Boot Image
aml_encrypt_g12b --imgsig --input boot.img --amluserkey aml-user-key.sig --output boot.img.encrypt
```

按道理该设备不存在运行自定义内核的可能，但是好像Amlogic的U-Boot只会校验Android Boot Image形式存在的内核，对直接加载内核不存在限制。所以可以使用厂商的U-Boot搭配自定义内核来启动系统

# 厂商U-Boot

厂商的U-Boot在cmd下输入任何命令都提示不存在，但在U-Boot script中却可以使用一些命令，可使用的命令列表在[available-cmd-list.txt](https://github.com/retro98boy/onethingcloud-oes-linux/releases/tag/v2025.06.27)

## 环境变量

该设备的eMMC使用的是Amlogic专有的MPT，使用`ampart /dev/mmcblk1`可以查看具体信息：

```
===================================================================================
ID| name            |          offset|(   human)|            size|(   human)| masks
-----------------------------------------------------------------------------------
 0: bootloader                      0 (   0.00B)           400000 (   4.00M)      0
    (GAP)                                                 2000000 (  32.00M)
 1: reserved                  2400000 (  36.00M)          4000000 (  64.00M)      0
    (GAP)                                                  800000 (   8.00M)
 2: cache                     6c00000 ( 108.00M)         20000000 ( 512.00M)      2
    (GAP)                                                  800000 (   8.00M)
 3: env                      27400000 ( 628.00M)           800000 (   8.00M)      0
    (GAP)                                                  800000 (   8.00M)
 4: logo                     28400000 ( 644.00M)           800000 (   8.00M)      1
    (GAP)                                                  800000 (   8.00M)
 5: recovery                 29400000 ( 660.00M)          1800000 (  24.00M)      1
    (GAP)                                                  800000 (   8.00M)
 6: misc                     2b400000 ( 692.00M)          2000000 (  32.00M)      1
    (GAP)                                                  800000 (   8.00M)
 7: dto                      2dc00000 ( 732.00M)           800000 (   8.00M)      1
    (GAP)                                                  800000 (   8.00M)
 8: cri_data                 2ec00000 ( 748.00M)           800000 (   8.00M)      2
    (GAP)                                                  800000 (   8.00M)
 9: param                    2fc00000 ( 764.00M)          1000000 (  16.00M)      2
    (GAP)                                                  800000 (   8.00M)
10: boot                     31400000 ( 788.00M)          2000000 (  32.00M)      1
    (GAP)                                                  800000 (   8.00M)
11: rsv                      33c00000 ( 828.00M)          1000000 (  16.00M)      1
    (GAP)                                                  800000 (   8.00M)
12: tee                      35400000 ( 852.00M)          2000000 (  32.00M)      1
    (GAP)                                                  800000 (   8.00M)
13: vendor                   37c00000 ( 892.00M)         10000000 ( 256.00M)      1
    (GAP)                                                  800000 (   8.00M)
14: odm                      48400000 (   1.13G)         10000000 ( 256.00M)      1
    (GAP)                                                  800000 (   8.00M)
15: system                   58c00000 (   1.39G)         40000000 (1024.00M)      1
    (GAP)                                                  800000 (   8.00M)
16: kernel                   99400000 (   2.39G)          2000000 (  32.00M)      2
    (GAP)                                                  800000 (   8.00M)
17: backup                   9bc00000 (   2.43G)         40000000 (1024.00M)      2
    (GAP)                                                  800000 (   8.00M)
18: instaboot                dc400000 (   3.44G)         20000000 ( 512.00M)      2
    (GAP)                                                  800000 (   8.00M)
19: data                     fcc00000 (   3.95G)         d5400000 (   3.33G)      4
===================================================================================
```

reserved分区的头部保存着MPT，env分区的头部保留着U-Boot的环境变量，可以使用以下命令备份MPT和U-Boot环境变量：

```bash
dd if=/dev/mmcblk1 of=./reserved bs=1MiB skip=36 count=64 status=progress
dd if=/dev/mmcblk1 of=./env.orig.bin bs=1MiB skip=628 count=8 status=progress
```

如果想将U-Boot环境变量改回刚刷完USB刷写包的状态，可以在[此处](https://github.com/retro98boy/onethingcloud-oes-linux/releases/tag/v2025.06.27)下载 env.orig.bin，使用dd命令刷回：

```bash
dd if=./env.orig.bin of=/dev/mmcblk1 bs=1MiB seek=628 status=progress
```

env分区只有前0x20000字节用于保存U-Boot环境变量，其中0x10000-0x1ffff字节用于冗余。在安装Armbian后，可以安装fw_printenv/fw_setenv来访问/修改U-Boot环境变量

下载主线U-Boot源码，使用`make khadas-vim3_defconfig && make CROSS_COMPILE=aarch64-linux-gnu- envtools`交叉编译得到fw_printenv，将其安装到Armbian的/usr/local/bin，然后建立fw_setenv的符号链接指向fw_printenv。或者直接使用`sudo apt install libubootenv-tool`来安装

建立fw_printenv/fw_setenv的配置文件`/etc/fw_env.config`：

```
/dev/mmcblk1 0x27400000 0x10000 0x27410000 0x10000
```

测试：

```bash
root@onethingcloud-oes:~# fw_setenv hello world
root@onethingcloud-oes:~# fw_printenv | grep hello
hello=world
```

# 安装Armbian

## 从U盘启动Armbian

下载ubuntu bionic USB刷写包和Armbian镜像

首先刷入ubuntu bionic系统，开机以后输入`fw_setenv upgrade_step 3`，插入刻录好Armbian镜像的U盘，再重启设备就会尝试从U盘启动

## 安装Armbian到eMMC

设备从U盘启动Armbian后，将Armbian镜像上传到设备中，然后执行`dd if=path-to-armbian.img of=/dev/mmcblk2 status=progress`将镜像刻录到eMMC，刻录完成后，断电**拔掉U盘**再重新上电即可

或者参考[此处](https://github.com/retro98boy/cainiao-cniot-core-linux)使用Netcat直接将Armbian镜像刻录到eMMC中，避免先上传到U盘中

上电前要拔掉U盘是因为eMMC的rootfs分区UUID和U盘上的冲突，因为它们来自同一个Armbian镜像

## 安装Armbian到SATA硬盘

由于该设备不存在SD卡槽，所以只能从eMMC加载FIP/U-Boot。又因为Secure Boot暂时只能使用厂商U-Boot，而厂商U-Boot没有从SATA加载内核的能力。所以只能将内核存放在eMMC上，然后从SATA硬盘上加载rootfs，这有两种实现办法：

一，通过cmdline直接让内核将SATA上的rootfs分区作为rootdev（推荐）

Armbian的rootdev在/boot/armbianEnv.txt中设置并在开机时作为cmdline的一部分传给内核

设备从U盘启动Armbian后，将Armbian镜像上传到设备中，使用`dd if=path-to-armbian.img of=/dev/mmcblk1 bs=1MiB count=1148 status=progress`将镜像前1148MiB刷写到eMMC上，这部分空间包括FIP，MPT，U-Boot env和boot分区

> 因为Armbian镜像的[配置](https://github.com/retro98boy/armbian-build/blob/main/config/boards/onethingcloud-oes.csc)为MPT和U-Boot env在开头保留636MiB空间，加上boot分区的512MiB空间，等于1148MiB

然后使用`cfdisk /dev/mmcblk1`进入TUI界面将第二个分区的信息从MBR分区表里面删除并保存退出

使用`dd if=path-to-armbian.img of=/dev/sdX status=progress`将Armbian镜像刻录到某个SATA硬盘，然后使用`cfdisk /dev/sdX`进入TUI界面，将第一个分区删除并保存退出。这是为了防止systemd在启动后，根据/etc/fstab中的设置挂载/boot时，会概率性从eMMC和SATA中二选一

做好以上步骤，重启设备即可

注意这个办法，如果SATA硬盘损坏/断开，设备会无法开机，因为内核找不到rootfs，开机串口log会提示找不到UUID

此时可以重新制作一个Armbian U盘，使用`sudo e2fsck -f /dev/sdX2 && sudo tune2fs /dev/sdX2 -U your-uuid && sudo e2fsck -f /dev/sdX2`更改rootfs分区的UUID让内核加载，别忘了也修改U盘上的/etc/fstab中的UUID

也可以在安装Armbian到SATA硬盘前，使用`fw_setenv autobootcmd "echo 'try boot from usb drive'; if usb start; then run try_usbdrive_bootcmd; fi; echo 'try boot from emmc'; run try_emmc_bootcmd; echo 'try boot from sdcard'; run try_sdcard_bootcmd; echo 'fallback to vendor boot'; run storeboot"`改变autobootcmd，让U-Boot优先扫描U盘上的boot.scr启动系统

二，将Armbian刷入eMMC，正常从eMMC启动Armbian，然后使用systemd switch-root到SATA上的rootfs，参考[jetsonhacks/rootOnNVMe](https://github.com/jetsonhacks/rootOnNVMe)

# pyamlboot

尝试使用pyamlboot加载FIP

![pyamlboot-fip](pictures/pyamlboot-fip.png)

![pyamlboot-fip-log](pictures/pyamlboot-fip-log.png)

TODO: 使用[superna9999/pyamlboot](https://github.com/superna9999/pyamlboot)自动化刷入Armbian到eMMC

# 相关链接

[Dumping the Amlogic A113X Bootrom](https://haxx.in/posts/dumping-the-amlogic-a113x-bootrom/)

[Raxone/Amlogic-exploit](https://github.com/Raxone/Amlogic-exploit)

[pre-generated-fip.rst](https://github.com/u-boot/u-boot/blob/master/doc/board/amlogic/pre-generated-fip.rst)

[aml_upgrade_pkg_gen.sh](https://github.com/hardkernel/buildroot/blob/master/package/aml_img_packer_new/src/aml_upgrade_pkg_gen.sh)
