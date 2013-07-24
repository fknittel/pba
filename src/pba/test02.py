#!/usr/bin/python
# vim:set ts=4 sw=4 et:
from __future__ import (absolute_import, division, print_function,
        unicode_literals)
from pba.gpio import GpioController
import time

ctrl = GpioController()

GPIO0_BASE = 0 * 32
GPIO1_BASE = 1 * 32
GPIO2_BASE = 2 * 32
GPIO3_BASE = 2 * 32

p_court1 = ctrl.export(GPIO2_BASE + 25)
p_court2 = ctrl.export(GPIO2_BASE + 24)
p_court3 = ctrl.export(GPIO2_BASE + 1)
p_court4 = ctrl.export(GPIO0_BASE + 27)
p_court5 = ctrl.export(GPIO2_BASE + 23)
p_court6 = ctrl.export(GPIO2_BASE + 22)
p_courts = [p_court1, p_court2, p_court3, p_court4, p_court5, p_court6]

for court in p_courts:
    court.turn_off()
pcounter = 0
while True:
    if pcounter < 6:
        p_court1.toggle()
    elif pcounter < 12:
        p_court2.toggle()
    elif pcounter < 18:
        p_court3.toggle()
    elif pcounter < 24:
        p_court4.toggle()
    elif pcounter < 30:
        p_court5.toggle()
    elif pcounter < 36:
        p_court6.toggle()
    elif pcounter < 42:
        for court in p_courts:
            court.toggle()
    pcounter += 1
    if pcounter == 42:
        pcounter = 0
    time.sleep(0.5)
