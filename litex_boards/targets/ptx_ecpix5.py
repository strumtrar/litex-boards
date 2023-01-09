#!/usr/bin/env python3

#
# This file is part of LiteX-Boards.
#
# Copyright (c) 2023 Steffen Trumtrar <kernel@pengutronix.de>
# SPDX-License-Identifier: BSD-2-Clause

from migen import *
import tempfile
import litex_boards.targets.lambdaconcept_ecpix5 as lc_ecpix5
from litex_boards.platforms import lambdaconcept_ecpix5
from litex.soc.integration.builder import *
from litex.soc.integration.soc import SoCRegion
from litex.soc.integration.soc_core import *
from litex.build.lattice.trellis import trellis_args, trellis_argdict
from litex.soc.cores.cpu.vexriscv_smp import VexRiscvSMP

class PtxSoC(lc_ecpix5.BaseSoC):
    def __init__(self, device="85F", sys_clk_freq=int(75e6),
        with_ethernet          = False,
        with_led_chaser        = False,
        with_ws2812            = True,
        with_rotary            = True,
        **kwargs):
        self.gateware_dir = ""

        kwargs["integrated_sram_size"] = 1024 * 6
        kwargs["integrated_rom_size"]  = 1024 * 64
        # use Wishbone and L2 for memory access
        kwargs["l2_size"] = 2048

        # SoCCore ----------------------------------------------------------------------------------
        super().__init__(device, sys_clk_freq, with_ethernet, with_led_chaser, **kwargs)

    def set_gateware_dir(self, gateware_dir):
        self.gateware_dir = gateware_dir

    def initialize_rom(self, data, args=[]):
        if args and args.no_compile_software:
            (_, path) = tempfile.mkstemp()
            subprocess.check_call(["ecpbram", "-g", path, "-w", str(self.rom.mem.width), "-d", str(int(self.integrated_rom_size / 4)), "-s" "0"])
            random_file = open(path, 'r')
            data = []
            random_lines = random_file.readlines()
            for line in random_lines:
                data.append(int(line, 16))

            os.remove(path)

        self.init_rom(name="rom", contents=data, auto_size=True)

        # Save actual expected contents for future use as gateware/mem.init
        content = ""
        formatter = "{:0" + str(int(self.rom.mem.width / 4)) + "X}\n"
        for d in data:
            content += formatter.format(d).zfill(int(self.rom.mem.width / 4))
        romfile = os.open(os.path.join(self.gateware_dir, "mem.init"), os.O_WRONLY | os.O_CREAT)
        os.write(romfile, content.encode())
        os.close(romfile)

def main():
    from litex.soc.integration.soc import LiteXSoCArgumentParser
    parser = LiteXSoCArgumentParser(description="LiteX SoC on ECPIX-5")
    target_group = parser.add_argument_group(title="Target options")
    target_group.add_argument("--build",           action="store_true", help="Build bitstream.")
    target_group.add_argument("--device",          default="85F",       help="ECP5 device (45F or 85F).")
    target_group.add_argument("--sys-clk-freq",    default=75e6,        help="System clock frequency.")
    target_group.add_argument("--with-sdcard",     action="store_true", help="Enable SDCard support.")
    ethopts = target_group.add_mutually_exclusive_group()
    ethopts.add_argument("--with-ethernet",  action="store_true", help="Enable Ethernet support.")

    builder_args(parser)
    soc_core_args(parser)
    trellis_args(parser)
    VexRiscvSMP.args_fill(parser)
    args = parser.parse_args()

    soc = PtxSoC(
        device                 = args.device,
        sys_clk_freq           = int(float(args.sys_clk_freq)),
        with_ethernet          = args.with_ethernet,
        **soc_core_argdict(args)
    )
    if args.with_sdcard:
        soc.add_sdcard()
    VexRiscvSMP.args_read(args)
    builder = Builder(soc, **builder_argdict(args))
    soc.set_gateware_dir(builder.gateware_dir)
    builder.build(**trellis_argdict(args), run=args.build)

    soc.initialize_rom([], args)

if __name__ == "__main__":
    main()
