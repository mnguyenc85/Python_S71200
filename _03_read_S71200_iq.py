#!/usr/bin/env python3
"""
Simple Tkinter UI for reading S7-1200 inputs/outputs
"""
import tkinter as tk
from tkinter import ttk
import _01_read_s71200 as s7conn

LED_OFF_COLOR = "#6e6e6e"
LED_ON_COLOR_IN = "#2ecc71"   # green for inputs
LED_ON_COLOR_OUT = "#f39c12"  # orange for outputs

class S7Ui(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("S7-1200 I/O Monitor")
        self.resizable(False, False)
        self._create_widgets()

    def _create_widgets(self):
        pad = 8
        main = ttk.Frame(self, padding=pad)
        main.grid(row=0, column=0, sticky="nsew")

        # Top: PLC address and port
        top = ttk.Frame(main)
        top.grid(row=0, column=0, sticky="w", pady=(0, pad))

        ttk.Label(top, text="PLC address:").grid(row=0, column=0, sticky="w")
        self.entry_addr = ttk.Entry(top, width=20)
        self.entry_addr.grid(row=0, column=1, sticky="w", padx=(4, 12))
        self.entry_addr.insert(0, "192.168.0.2")

        ttk.Label(top, text="Port:").grid(row=0, column=2, sticky="w")
        self.entry_port = ttk.Entry(top, width=8)
        self.entry_port.grid(row=0, column=3, sticky="w", padx=(4, 12))
        self.entry_port.insert(0, "102")

        self.btn_read = ttk.Button(top, text="Read", command=self.on_read_pressed)
        self.btn_read.grid(row=0, column=4)

        # Middle: Inputs and Outputs
        io_frame = ttk.Frame(main)
        io_frame.grid(row=1, column=0, sticky="nsew")

        # Inputs
        in_frame = ttk.LabelFrame(io_frame, text="Inputs (I)")
        in_frame.grid(row=0, column=0, padx=(0, 12))
        self.in_leds = []
        self._create_led_grid(parent=in_frame, leds_list=self.in_leds, count=16, is_input=True)

        # Outputs
        out_frame = ttk.LabelFrame(io_frame, text="Outputs (Q)")
        out_frame.grid(row=0, column=1)
        self.out_leds = []
        self._create_led_grid(parent=out_frame, leds_list=self.out_leds, count=16, is_input=False)

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status = ttk.Label(main, textvariable=self.status_var, relief=tk.SUNKEN, anchor="w", padding=(4,2))
        status.grid(row=2, column=0, sticky="we", pady=(8,0))

    def _create_led_grid(self, parent, leds_list, count=16, is_input=True):
        # Creates a grid of small canvases each containing an oval to represent an LED
        cols = 8
        rows = (count + cols - 1) // cols
        led_size = 14
        pad = 6
        for i in range(count):
            r = i // cols
            c = i % cols
            cell = ttk.Frame(parent, width=led_size+pad, height=led_size+24)
            cell.grid_propagate(False)
            cell.grid(row=r, column=c, padx=4, pady=4)

            canvas = tk.Canvas(cell, width=led_size, height=led_size, highlightthickness=0)
            canvas.grid(row=0, column=0, pady=(2,0))
            # draw oval (circle)
            oval = canvas.create_oval(1, 1, led_size-1, led_size-1, fill=LED_OFF_COLOR, outline='')

            label = ttk.Label(cell, text=str(i), anchor="center")
            label.grid(row=1, column=0)

            # store tuple (canvas, oval) so we can change color later
            leds_list.append((canvas, oval))

            # allow clicking LED to toggle (useful for testing)
            def make_toggle(ind, canvas=canvas):
                return lambda e: self._toggle_led_by_index(ind, is_input)
            if not is_input:
              canvas.bind("<Button-1>", make_toggle(i))

    def _toggle_led_by_index(self, index, is_input=True):
        # Toggle LED state for testing/demo
        leds = self.in_leds if is_input else self.out_leds
        canvas, oval = leds[index]
        current = canvas.itemcget(oval, 'fill')
        on_color = LED_ON_COLOR_IN if is_input else LED_ON_COLOR_OUT
        new = LED_OFF_COLOR if current == on_color else on_color
        canvas.itemconfigure(oval, fill=new)

    def set_input(self, index, state: bool):
        """Set input LED (index 0..15) to state True(on)/False(off)"""
        if 0 <= index < len(self.in_leds):
            canvas, oval = self.in_leds[index]
            canvas.itemconfigure(oval, fill=LED_ON_COLOR_IN if state else LED_OFF_COLOR)

    def set_output(self, index, state: bool):
        """Set output LED (index 0..15) to state True(on)/False(off)"""
        if 0 <= index < len(self.out_leds):
            canvas, oval = self.out_leds[index]
            canvas.itemconfigure(oval, fill=LED_ON_COLOR_OUT if state else LED_OFF_COLOR)

    def on_read_pressed(self):
        # Placeholder: user requested to implement real read logic later.
        # Here we only update the status and print to console for debugging.
        addr = self.entry_addr.get().strip()
        port = int(self.entry_port.get().strip())
        self.status_var.set(f"Read pressed — addr={addr} port={port}")
        print(f"Read pressed — addr={addr} port={port}")
        # TODO: Implement S7-1200 read logic here (e.g. using python-snap7 or snap7)
        # Example: connect, read inputs/outputs, then call set_input/set_output for each bit.
        output_buf = s7conn.read_output(addr, port)
        mask = 1
        for i in range(16):
            byte_i = int(i / 8)
            self.set_output(i, output_buf[byte_i] & mask == mask)
            mask = mask << 1


if __name__ == '__main__':
    app = S7Ui()
    app.mainloop()
