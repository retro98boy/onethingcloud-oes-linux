#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0 OR MIT
# -*- coding: utf-8 -*-

__license__ = "GPL-2.0"
__copyright__ = "Copyright (c) 2024, SaluteDevices"
__version__ = "0.0.1"

import argparse
import logging
import sys
from enum import Enum

from pyamlboot.amlimage import AmlImagePack
from pyamlboot.optimus import *


class WipeFormat(Enum):
    no = 0
    normal = 1
    all = 3

    def __str__(self):
        return self.name


class BurnStepArmbian(BurnStepBase):
    def __init__(self, shared_data, *args, **kwargs):
        super().__init__(shared_data)
        self.armbian_path = kwargs["armbian_path"]
        self._title = f"Burn Armbian {self.armbian_path}"
        self._timeout = kwargs.get("timeout", 3000)

    def split_data_to_emmc(
        self, data, chunk_size, dev, download_ddr_address, emmc_start_block
    ):
        """将数据分块传入内存并写入eMMC"""
        sub_chunk_size = 4096  # 每次writeLargeMemory的大小（字节）
        emmc_block_size = 512  # eMMC块大小（字节）
        blocks_per_chunk = chunk_size // emmc_block_size  # 每个分块的eMMC块数
        chunk_index = 0

        while True:
            start = chunk_index * chunk_size
            chunk_data = data[start : start + chunk_size]
            if not chunk_data:
                break
            # 将分块分多次传入内存
            print(f"正在将分块{chunk_index}传入内存地址0x{download_ddr_address:08x}")
            total_sub_chunks = (len(chunk_data) + sub_chunk_size - 1) // sub_chunk_size
            for i in range(0, len(chunk_data), sub_chunk_size):
                sub_chunk = chunk_data[i : i + sub_chunk_size]
                sub_chunk_offset = download_ddr_address + i
                dev.writeLargeMemory(sub_chunk_offset, sub_chunk, sub_chunk_size)
                # 单行动态更新子块写入进度
                print(
                    f"  子块{i // sub_chunk_size}/{total_sub_chunks - 1}传入内存地址0x{sub_chunk_offset:08x}({len(sub_chunk)}字节)",
                    end="\r",
                )
            # 最后一个子块后换行
            print()

            # 使用mmc write将整个分块写入eMMC
            offset = emmc_start_block + chunk_index * blocks_per_chunk
            self._check_bulk_cmd(
                f"mmc write {download_ddr_address:08x} {offset:08x} {blocks_per_chunk:08x}",
                timeout=self._timeout,
            )
            print(f"已将分块{chunk_index}写入eMMC偏移{offset}（块）")

            chunk_index += 1
        return chunk_index

    def do(self, dev):
        self._dev = dev

        with open(self.armbian_path, "rb") as f:
            logging.info("将Armbian镜像的前4MiB写入eMMC，包含FIP和MBR")
            f.seek(0)
            fipmbr_data = f.read(4 * 1024 * 1024)
            self.split_data_to_emmc(
                fipmbr_data, 4 * 1024 * 1024, self._dev, 0x20000000, 0
            )

            logging.info("将Armbian镜像中的boot分区写入eMMC")
            boot_offset = 636 * 1024 * 1024
            boot_size = 512 * 1024 * 1024
            f.seek(boot_offset)
            boot_data = f.read(boot_size)
            boot_emmc_start_block = boot_offset // 512
            self.split_data_to_emmc(
                boot_data,
                512 * 1024 * 1024,
                self._dev,
                0x20000000,
                boot_emmc_start_block,
            )

            logging.info("将Armbian镜像中的rootfs分区写入eMMC")
            rootfs_offset = (636 + 512) * 1024 * 1024
            f.seek(rootfs_offset)
            rootfs_data = f.read()  # 读取剩余部分
            rootfs_emmc_start_block = rootfs_offset // 512
            self.split_data_to_emmc(
                rootfs_data,
                512 * 1024 * 1024,
                self._dev,
                0x20000000,
                rootfs_emmc_start_block,
            )

        logging.info("设置U-Boot的bootcmd")
        logging.info("由于bulk cmd的127字符限制，只设置从eMMC启动")
        logging.info(
            "如果想打开U盘启动功能，可以在Armbian开机后使用fw_setenv设置相应的环境变量"
        )
        logging.info(
            "参考：https://github.com/retro98boy/onethingcloud-oes-linux/blob/blobs/aml_autoscript.cmd"
        )
        self._check_bulk_cmd(
            "setenv bootcmd 'echo '**********run auto boot cmd**********'; run autobootcmd'"
        )
        self._check_bulk_cmd(
            "setenv autobootcmd 'echo 'try boot from emmc'; run try_emmc_bootcmd;'"
        )
        self._check_bulk_cmd(
            "setenv try_emmc_bootcmd 'if fatload mmc 1 1020000 boot.scr; then setenv devtype mmc; setenv devnum 1; autoscr 1020000; fi'"
        )
        self._check_bulk_cmd("saveenv")


def setup_armbian(args, aml_img):
    shared_data = SharedData()
    burn_steps = get_burn_steps(args, shared_data, aml_img)

    if args.usbboot:
        burn_steps.insert(
            len(burn_steps) - 1,
            BurnStepCommand(shared_data, cmd="setenv upgrade_step 3 && saveenv"),
        )
    else:
        burn_steps.insert(
            len(burn_steps) - 1,
            BurnStepArmbian(shared_data, armbian_path=args.armbian.name, timeout=30000),
        )

    do_burn(burn_steps)


def main():
    logging.basicConfig(
        level=logging.DEBUG,
        format="[%(asctime)s] [%(levelname)-8s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--img",
        required=True,
        type=argparse.FileType("rb"),
        help="Specify location path to aml_upgrade_package.img",
    )
    parser.add_argument(
        "--armbian",
        required=False,
        type=argparse.FileType("rb"),
        help="Specify location path to Armbian image",
    )
    parser.add_argument(
        "--usbboot",
        action="store_true",
        default=False,
        help="Setup USB boot",
    )
    parser.add_argument(
        "--reset", action="store_true", default=False, help="Reset after success"
    )
    parser.add_argument(
        "--no-erase-bootloader",
        action="store_true",
        default=False,
        help="Erase bootloader",
    )
    parser.add_argument(
        "--wipe",
        type=lambda x: WipeFormat[x],
        choices=list(WipeFormat),
        default="normal",
        help="Destroy all partitions",
    )
    parser.add_argument(
        "--password",
        type=argparse.FileType("rb"),
        help="Unlock usb mode using password file provided",
    )
    parser.add_argument("--version", action="version", version=__version__)

    args = parser.parse_args()
    aml_img = AmlImagePack(args.img, True)
    setup_armbian(args, aml_img)


if __name__ == "__main__":
    sys.exit(main())
