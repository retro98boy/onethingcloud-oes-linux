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

    def write_data_to_emmc(
        self,
        data,
        dev,
        download_ddr_address,
        emmc_start_block,
        chunk_size=512 * 1024 * 1024,
    ):
        """将单个512MiB数据块传入内存并写入eMMC"""
        sub_chunk_size = 1024 * 1024  # 每次writeLargeMemory的大小（字节）
        emmc_block_size = 512  # eMMC块大小（字节）
        blocks_per_chunk = chunk_size // emmc_block_size  # 分块的eMMC块数

        # 直接处理传入的数据块
        print(f"正在将数据块传入内存地址0x{download_ddr_address:08x}")
        total_sub_chunks = (len(data) + sub_chunk_size - 1) // sub_chunk_size
        for i in range(0, len(data), sub_chunk_size):
            sub_chunk = data[i : i + sub_chunk_size]
            sub_chunk_offset = download_ddr_address + i
            dev.writeLargeMemory(sub_chunk_offset, sub_chunk, sub_chunk_size)
            # 单行动态更新子块写入进度
            print(
                f"  子块{i // sub_chunk_size}/{total_sub_chunks - 1}传入内存地址0x{sub_chunk_offset:08x}({len(sub_chunk)}字节)",
                end="\r",
            )
        # 最后一个子块后换行
        print()

        # 使用mmc write将整个数据块写入eMMC
        self._check_bulk_cmd(
            f"mmc write {download_ddr_address:08x} {emmc_start_block:08x} {blocks_per_chunk:08x}",
            timeout=self._timeout,
        )
        print(f"已将数据块写入eMMC偏移{emmc_start_block}（块）")

    def do(self, dev):
        self._dev = dev
        chunk_size = 512 * 1024 * 1024  # 512MiB

        with open(self.armbian_path, "rb") as f:
            logging.info("开始写入镜像到eMMC")
            emmc_start_block = 0  # 从eMMC的起始块开始
            chunk_index = 0

            while True:
                # 每次读取512MiB数据
                chunk_data = f.read(chunk_size)
                if not chunk_data:
                    break
                logging.info(f"读取分块{chunk_index}（{len(chunk_data)}字节）")
                # 将读取的分块写入eMMC
                self.write_data_to_emmc(
                    chunk_data,
                    self._dev,
                    0x20000000,
                    emmc_start_block + (chunk_index * (chunk_size // 512)),
                )
                chunk_index += 1

        logging.info("设置U-Boot的bootcmd")
        logging.info("由于bulk cmd的127字符限制，只设置从eMMC启动")
        logging.info(
            "如果想打开U盘启动功能，可以在Armbian开机后使用fw_setenv设置相应的环境变量"
        )
        logging.info(
            "参考：https://github.com/retro98boy/onethingcloud-oes-linux/blob/oes-blobs/aml_autoscript.cmd"
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
