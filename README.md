# 🎮 plover_controller

This plugin was designed for use with [Open Steno Project's Plover](https://openstenoproject.org).
With only a video game controller, you can harness the power of machine stenography, a shorthand writing system that's been proven effective since its inception in 1879.
To this day, stenography is trusted for use in live captioning and court reporting, due to its high speed and accuracy.


> [!WARNING]
> plover_controller may not work on macOS. Only Windows and Linux have been tested successfully.

## Table of Contents

1. [Learning Resources](#learning-resources)
1. [Installation](#installation)
1. [Usage](#usage)
    1. [Examples](#examples)
1. [Setup](#setup)
    1. [Mapping Buttons](#mapping-buttons)
1. [The Default Map](#the-default-map)
    1. [Left Joystick](#left-joystick)
    1. [Right Joystick](#right-joystick)
    1. [Buttons](#right-joystick)
1. [Default mapping image](#default-mapping-image)

## Learning resources

To get started with controller steno, check out these fantastic [learning resources on the Plover wiki](https://github.com/openstenoproject/plover/wiki/Learning-Stenography)!
Need assistance or just want to chat about steno? Join the lively steno community on the [Plover Discord](https://discord.com/invite/0lQde43a6dGmAMp2)

## Installation

We recommend installation via Plover's built-in Plugins Manager.
For manual installation, follow [the step-by-step guide in the Plover documentation](https://plover.readthedocs.io/en/latest/cli_reference.html#plugin-installer).

## Usage

Stenography is a phonetic/mnemonic shorthand writing system.
It is predominantly written based on sound in Plover theory.

Plover processes the keys in the following order, known as "steno order":
`STKPWHRAO*EUFRPBLGTSDZ`.

In the default configuration:

- The left joystick handles the beginning consonants `STKPWHR-`
- The shoulder buttons and triggers handle the vowels `AOEU`
- The right joystick and ABXY buttons handle `*` and the ending consonants `-FRPBLGTSDZ`.

To see which characters are being registered, open the **Paper Tape** window in Plover.

### Examples

Let's say you wanted to write the word "cat".
In Plover theory, cat is written like `KAT`.
To write "cat" with your controller, do the following simultaneously:

1. Move the left joystick down and to the left for the starting consonant `K-`
2. Press the left trigger button for the vowel `A`
3. Press the X button for the ending consonant `-T`

Finally, release the joystick, trigger, and X button, which should output "cat".

Here's a slightly more difficult one, "straps".
Do the following, keeping at least one button pressed or joystick moved before releasing to end the stroke:

1. Press the left joystick for `S-`
2. Move the left joystick up and to the left for `T-`
3. Move the left stick to the bottom right for `R-`
4. Press the left trigger for `A`
5. Move the right joystick to the top for `-P`
6. Press the A button (Xbox layout A) for `-S`

Release to end the stroke, and you should get the output `straps`.

## Setup

Once the plugin is installed and Plover has been restarted, Plover's **Machine** select box should now have a **Controller** option.

The settings for **plover_controller** can be found in the Plover Configuration under the **Machine** tab.

### Mapping buttons

The default configuration was created for use with an Xbox Elite controller.
If you are using any other controller, you will likely have to change the default key mapping in the Plover Machine settings.

Any problems will most likely be due to your button map. The best way to resolve these issues is to:

- Open the Plover **Machine** Configuration menu.
- Move the joystick or press the button causing problems
- Observe the text output in the **Last axis event** and **Last other event** fields at the bottom of the **Options** section, and compare it to the text in the **Mapping** field. Make changes as needed.

## Default mapping

### Left joystick

```
         -----------------
      /   \             /   \
     /     \    P-     /     \
    /       \         /       \
   /   T-    \_______/    H-   \
  /          /       \          \
 /          /         \          \
 +---------|     S-    |---------+
 \          \         /          /
  \          \       /          /
   \   K-     \_____/     R-   /
    \        /       \        /
     \      /    W-   \      /
      \    /           \   /
         -----------------
```
### Right joystick

```
         -----------------
      /   \             /   \
     /     \    -P     /     \
    /       \         /       \
   /   -F    \_______/    -L   \
  /          /       \          \
 /          /         \          \
 +---------|     *     |---------+
 \          \         /          /
  \          \       /          /
   \   -R     \_____/     -G   /
    \        /       \        /
     \      /   -B    \      /
      \    /           \    /
         -----------------
```

### Buttons

| Button (Xbox Labels)     | Maps To  |
|--------------------------|----------|
| Left Trigger / Paddle 4  | A        |
| Left Bumper / Paddle 3   | O        |
| Right Bumper / Paddle 1  | E        |
| Right Trigger / Paddle 2 | U        |
| Select                   | *        |
| Start                    | #        |
| X Button                 | -T       |
| A Button                 | -S       |
| Y Button                 | -D       |
| B Button                 | -Z       |

## Default mapping image

![Default mapping](https://github.com/tadeokondrak/plover_controller/assets/4098453/f2883413-c177-4c0c-80aa-778b11a5173b)

