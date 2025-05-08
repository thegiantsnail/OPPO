#!/usr/bin/env python3
"""FM Synth with Xbox 360 Controller Interface"""
import argparse
import sys
import random
import numpy as np
import sounddevice as sd
import pygame
from pygame.locals import QUIT, JOYBUTTONDOWN, JOYAXISMOTION


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
        s = self.op1.sOscFM(t, self.note_on, self.note_off, self.op2.sOsc(t, self.note_on, self.note_off), self.op2.k)
        s += self.op3.sOscFM(t, self.note_on, self.note_off, self.op4.sOsc(t, self.note_on, self.note_off), self.op4.k)

        if t > self.note_off + max(self.op1.r, self.op3.r) + 0.25:
            self.reset()
        return s

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

    def __init__(self, i=1, f=440.0, a=0.1, d=0.1, s=1.0, r=0.1, k=1.0):
        self.index = i
        self.f = f
        self.a = a
        self.d = d
        self.s = s
        self.r = r
        self.k = k

    def sineIndex(self, t):
        return int((self.f * t) % 1 * self.tableLength)

    def sOscFM(self, t, note_on, note_off, msamp, mk):
        index = (self.sineIndex(t) + int(mk * msamp)) % self.tableLength
        return self.sAmp(t, note_on, note_off) * self.sine[index]

    def sOsc(self, t, note_on, note_off):
        return self.sAmp(t, note_on, note_off) * self.sine[self.sineIndex(t)]

    def sAmp(self, time, note_on, note_off):
        l = time - note_on
        if note_on > note_off:  # Note is held
            if l < self.a:
                return (l / self.a)
            elif l < self.a + self.d:
                return ((l - self.a) / self.d) * (self.s - 1) + 1
            else:
                return self.s
        else:
            r_time = time - note_off
            if r_time < self.r:
                return self.s * (1 - r_time / self.r)
            else:
                return 0.0

    def randomize(self):
        self.f = round(0.01 + random.random() * 440, 2)
        self.a = round(0.1 + random.random() * 2, 2)
        self.d = round(0.01 + random.random() * 2, 2)
        self.s = round(0.01 + random.random(), 2)
        self.r = round(0.1 + random.random() * 2, 2)
        self.k = round(0.01 + random.random() * 2000, 2)

    def dump(self):
        print(f"OP: F:{self.f:.2f} K:{self.k:.2f} ADSR:[{self.a:.2f}, {self.d:.2f}, {self.s:.2f}, {self.r:.2f}]")


def xego_interface(voice):
    pygame.init()
    screen = pygame.display.set_mode((400, 300))
    pygame.display.set_caption("Xego Controller Interface")
    font = pygame.font.Font(None, 36)

    clock = pygame.time.Clock()
    running = True

    # Initialize joystick
    pygame.joystick.init()
    if pygame.joystick.get_count() == 0:
        print("No joystick detected!")
        return
    joystick = pygame.joystick.Joystick(0)
    joystick.init()

    while running:
        screen.fill((0, 0, 0))
        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            elif event.type == JOYBUTTONDOWN:
                # Map buttons to actions
                if event.button == 0:  # Button A
                    voice.op1.f += 10  # Increase pitch
                elif event.button == 1:  # Button B
                    voice.op1.f -= 10  # Decrease pitch
                elif event.button == 2:  # Button X
                    voice.op1.k += 0.1  # Increase modulation
                elif event.button == 3:  # Button Y
                    voice.op1.k -= 0.1  # Decrease modulation
                print(f"Button {event.button} pressed")
            elif event.type == JOYAXISMOTION:
                # Map axes to continuous changes
                if event.axis == 0:  # Left stick horizontal
                    voice.op1.f += event.value * 5  # Adjust pitch
                elif event.axis == 1:  # Left stick vertical
                    voice.op1.k += event.value * 0.5  # Adjust modulation
                print(f"Axis {event.axis} moved to {event.value}")

        # Display joystick state
        for i in range(joystick.get_numbuttons()):
            text = font.render(f"Button {i}: {joystick.get_button(i)}", True, (255, 255, 255))
            screen.blit(text, (20, 20 + i * 20))

        # Display current pitch and modulation
        pitch_text = font.render(f"Pitch: {voice.op1.f:.2f} Hz", True, (255, 255, 255))
        modulation_text = font.render(f"Modulation: {voice.op1.k:.2f}", True, (255, 255, 255))
        screen.blit(pitch_text, (20, 200))
        screen.blit(modulation_text, (20, 230))

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()


def int_or_str(text):
    """Helper function to interpret text as an int or string."""
    try:
        return int(text)
    except ValueError:
        return text


def main():
    parser = argparse.ArgumentParser(description="FM Synth with Xbox 360 Controller Interface")
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
            xego_interface(voice)
    except KeyboardInterrupt:
        print("Exiting...")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
