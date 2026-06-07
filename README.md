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
1. [Advanced: Driver Settings](#advanced-driver-settings)
1. [Linux: Share Button and Extra Buttons](#linux-share-button-and-extra-buttons)
1. [Windows: Guide and Share Button](#windows-guide-and-share-button)
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

### D-Pad

The D-pad directions can be combined by visiting multiple positions before releasing — just like building a chord. Larger combos are matched first, so pressing Up then Left in one motion gives you `KPA*D`, not `KPA` + `SKWH` separately.

| Direction(s)       | Stroke    | Purpose              |
|--------------------|-----------|----------------------|
| Up                 | `KPA`     | Capitalize next word |
| Down               | `HRO*ER`  | Lowercase next word  |
| Left               | `SKWH`    | Symbols starter ([Emily's Symbols](https://github.com/EPLHREU/emily-symbols)) |
| Right              | `SKP`     | "and"                |
| Up + Left          | `KPA*D`   | Capitalize last word |
| Down + Left        | `HRO*ERD` | Lowercase last word  |
| Down + Right       | `-LTZ`    | Commands ender ([Emily's Modifiers](https://github.com/EPLHREU/emily-modifiers)) |
| 8 other combos     | *(empty)* | Ready to map         |

> [!TIP]
> To hit a combo like Down + Right, slide the D-pad from one direction to the other before releasing. As long as at least one other input (stick, button, trigger) is held or the D-pad doesn't pass through center, the stroke stays open.

## Advanced: Driver Settings

The Machine settings include an **Advanced: Driver Settings** section with options that control how SDL2 communicates with your controller. Most users should not need to change these. Restart Plover after changing any of these settings.

> [!WARNING]
> Changing driver settings can alter how your controller is detected. Button and axis numbers may change, which will break your current hardware mappings.

| Setting | Default | Description |
|---------|---------|-------------|
| **Use HIDAPI driver** | On | Communicates with the controller using the cross-platform HIDAPI library instead of the OS-specific driver. This enables the GameController API, which provides standardized button names (e.g., `a`, `leftshoulder`, `guide`) instead of raw numbers. Disable this if your controller is not being detected or if you need raw button numbers for a non-standard controller. |
| **Use raw input driver** | Off | Uses the Windows Raw Input API to read controller data. **Windows only** — has no effect on Linux or macOS. May help if your controller isn't detected through the default Windows driver. |
| **Correlate raw input with XInput** | Off | When raw input is enabled, attempts to match raw input devices with their XInput equivalents for better button mapping. **Windows only.** |
| **Use background joystick thread** | Off | Polls for controller events on a dedicated background thread instead of the main SDL event loop. May improve responsiveness in some configurations, but can cause issues with certain drivers. |

## Linux: Share Button and Extra Buttons

On Linux, the default `xpad` kernel driver does not expose the share button on Xbox controllers. To enable it, you can use the [xone](https://github.com/medusalix/xone) driver instead.

### Arch Linux (AUR)

```bash
yay -S xone-dkms
```

### Other Distributions

Follow the [xone installation instructions](https://github.com/medusalix/xone#installation) to build and install from source. You will need `dkms`, `cabextract`, and Linux headers for your kernel.

### Setup

After installing xone, blacklist the default `xpad` driver and load the xone modules:

```bash
# Blacklist xpad so xone can claim the controller
echo "blacklist xpad" | sudo tee /etc/modprobe.d/blacklist-xpad.conf

# Unload xpad and load xone
sudo modprobe -r xpad
sudo modprobe xone_gip
sudo modprobe xone_gip_gamepad
sudo modprobe xone_wired
```

Then unplug and replug your controller. The share button should now appear as `misc1` in the Hardware tab.

> [!NOTE]
> Some controllers (like the PowerA Xbox Series X) have programmable back buttons that function as hardware remaps rather than independent inputs. To assign a back button, hold it and press the button you want it to duplicate.

## Windows: Guide and Share Button

On Windows 11, the Xbox Game Bar and Windows capture shortcuts intercept the Guide (Xbox) button and Share button before they reach Plover. To use these buttons for steno, you need to disable Game Bar, Controller Bar, and the Share button capture shortcut.

### Step 1: Disable Game Bar

1. Open **Settings** > **Gaming** > **Xbox Game Bar**
2. Toggle off **Allow your controller to open Game Bar**

### Step 2: Disable Controller Bar

The Controller Bar is a separate feature that also intercepts the Guide button:

1. Open Game Bar by pressing **Win+G**
2. Click the **gear icon** (Settings)
3. Go to **More settings** > **Shortcuts**
4. Uncheck **Open Controller Bar using button on a controller not over a game**

### Step 3: Disable Share Button Capture

Windows 11 maps the Share button to a screenshot/capture shortcut by default:

1. Open **Settings** > **Gaming** > **Captures**
2. Toggle off **Record what happened** (if enabled)
3. Open **Settings** > **Accessibility** > **Keyboard**
4. Under **On-screen keyboard, access keys, and Print Screen**, toggle off **Use the Print Screen key to open screen capture**

If the Share button still doesn't work after these steps, check that no other capture software (e.g., GeForce Experience, AMD Software) is intercepting it.

### Alternative: Registry Fix

You can disable the Controller Bar via registry instead of Step 2:

```
HKEY_CURRENT_USER\SOFTWARE\Microsoft\GameBar\UseNexusForGameBarEnabled
```

Set this DWORD value to `0`.

### Alternative: Remove Game Bar Entirely

If you don't use Game Bar at all, you can uninstall it via PowerShell:

```powershell
Get-AppxPackage Microsoft.XboxGamingOverlay | Remove-AppxPackage
```

> [!NOTE]
> All three steps may be required for full access. After making these changes, the Guide button should appear as `guide` and the Share button as `misc1` in the Hardware tab.

## Default mapping image

![Default mapping](https://github.com/tadeokondrak/plover_controller/assets/4098453/f2883413-c177-4c0c-80aa-778b11a5173b)

