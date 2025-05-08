#!/usr/bin/env python3
"""FM Synth"""
import argparse
import sys
import random
import numpy as np
import sounddevice as sd
import time as pytime


class Voice:
    def __init__(self, op1=None, op2=None, op3=None, op4=None):
        self.op1 = op1 if op1 else Operator()
        self.op2 = op2 if op2 else Operator()
        self.op3 = op3 if op3 else Operator()
        self.op4 = op4 if op4 else Operator()
        self.note_on = 0.0
        self.note_off = 0.0
        self.z = np.vectorize(self.sampleAt)

    def envLength(self):
        return max(self.op1.a, self.op2.a, self.op3.a, self.op4.a) + \
               max(self.op1.d, self.op2.d, self.op3.d, self.op4.d) + \
               0.25 + max(self.op1.r, self.op2.r, self.op3.r, self.op4.r)

    def sampleAt(self, t):
        try:
            s = self.op1.sOscFM(t, self.note_on, self.note_off, self.op2.sOsc(t, self.note_on, self.note_off), self.op2.k)
            s += self.op3.sOscFM(t, self.note_on, self.note_off, self.op4.sOsc(t, self.note_on, self.note_off), self.op4.k)

            if t > self.note_off + max(self.op1.r, self.op3.r) + 0.25:
                self.reset()
            return s
        except Exception as e:
            print(f"Error in sampleAt: {e}")
            return 0.0

    def reset(self):
        self.op1.randomize()
        self.op2.randomize()
        self.op3.randomize()
        self.op4.randomize()
        new = self.envLength()
        self.note_on = self.note_on + new
        self.note_off = self.note_on + new
        self.dump()

    def dump(self):
        self.op1.dump()
        self.op2.dump()
        self.op3.dump()
        self.op4.dump()
        print("RATIOS:", round(self.op2.f / self.op1.f, 2), round(self.op4.f / self.op3.f, 2))
        print("")


class Operator:
    tau = 2 * np.pi
    tableLength = 256
    sine = np.sin(np.linspace(0, 2 * np.pi, tableLength, endpoint=False))

    def __init__(self, f=440.0, a=0.1, d=0.1, s=1.0, r=0.1, k=1.0):
        self.f = f  # frequency
        self.a = a  # attack time
        self.d = d  # decay time
        self.s = s  # sustain level
        self.r = r  # release time
        self.k = k  # level / fm index

    def sineIndex(self, t):
        return int((self.f * t) % 1 * self.tableLength)

    def sOscFM(self, t, note_on, note_off, msamp, mk):
        index = (self.sineIndex(t) + int(mk * msamp)) % self.tableLength
        return self.sAmp(t, note_on, note_off) * self.sine[index]

    def sOsc(self, t, note_on, note_off):
        return self.sAmp(t, note_on, note_off) * self.sine[self.sineIndex(t)]

    def sAmp(self, time, note_on, note_off):
        amp = 0.0
        l = time - note_on

        if note_on > note_off:
            if l < self.a:
                amp = l / self.a
            elif l < self.a + self.d:
                amp = ((l - self.a) / self.d) * (self.s - 1) + 1
            else:
                amp = self.s
        else:
            amp = ((time - note_off) / self.r) * (0.0 - self.s) + self.s

        return max(0.0, amp)

    def randomize(self):
        self.f = round(0.01 + random.random() * 440, 2)
        self.a = round(0.1 + random.random() * 2, 2)
        self.d = round(0.01 + random.random() * 2, 2)
        self.s = round(0.01 + random.random(), 2)
        self.r = round(0.1 + random.random() * 2, 2)
        self.k = round(0.01 + random.random() * 2000, 2)

    def dump(self):
        print(f"OP: F:{self.f:.2f} K:{self.k:.2f} ADSR:[{self.a:.2f}, {self.d:.2f}, {self.s:.2f}, {self.r:.2f}]")


def int_or_str(text):
    try:
        return int(text)
    except ValueError:
        return text


def main():
    parser = argparse.ArgumentParser(description="FM Synth")
    parser.add_argument('-d', '--device', type=int_or_str, help='output device (numeric ID or substring)')
    parser.add_argument('-a', '--amplitude', type=float, default=0.2, help='amplitude (default: %(default)s)')
    args = parser.parse_args()

    voice = Voice()

    try:
        samplerate = sd.query_devices(args.device, 'output')['default_samplerate']

        def callback(outdata, frames, time, status):
            if status:
                print(status, file=sys.stderr)
            t = (np.arange(frames) / samplerate).reshape(-1, 1)
            outdata[:] = args.amplitude * voice.z(t)

        with sd.OutputStream(device=args.device, channels=1, callback=callback, samplerate=samplerate):
            print("Press Enter to stop...")
            input()
    except KeyboardInterrupt:
        print("Exiting...")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
