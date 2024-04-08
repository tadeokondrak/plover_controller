# Configuration file syntax

## Comments

Empty lines and lines starting with `//` are ignored.

## Stick definition


Example:

```
left stick has segments (dr,d,dl,ul,u,ur) on axes 0 and 1 offset by 0 degrees
right stick has segments (dr,d,dl,ul,u,ur) on axes 3 and 4 offset by 0 degrees
```

Syntax:

```
<stick-name> stick has segments (<stick-segments>) on axes <x-axis-number> and <y-axis-number> offset by <offset-amount> degrees
```

There can be any number of segments.

## Trigger definition

Example:

```
trigger on axis 2 is lefttrigger
trigger on axis 5 is righttrigger
```

Syntax:

```
trigger on axis <axis-number> is <axis-name>
```

## Button/hat definition

Example:

```
button 0 is a
button 1 is b
button 2 is x
button 3 is y

hat 0 is dpad
```

Syntax:

```
button <button-number> is <button-name>
hat <hat-number> is <hat-name>
```

## Button/trigger mappings

Example:

```
a -> -S
b -> -Z
x -> -T
y -> -D

lefttrigger -> A-
righttrigger -> -U
```

Syntax:

```
<name> -> <stroke>
```

## Simple stick/hat mappings

Example:

```
leftdr -> R-
leftd -> W-
leftdl -> K-

rightdr -> -G
rightd -> -B
rightdl -> -R

dpaddr -> -G
dpadd -> -B
dpaddl -> -R
```

Syntax:

Same as button and trigger mappings, but the stick direction is added to the end of the stick name.


## Complex stick mappings

Example:

```
left(d,dl,ul,dl) -> TW-
left(d,dl,ul,u,ul) -> KPW-
left(d,dl,ul,u,ul,dl,d) -> PW-
left(d,dl,ul,u,ul,dl) -> TPW-
```

Syntax:

```
<name>(<segments>) -> <stroke>
```

Note: This is not implemented for hats. Please open an issue if you want this behavior.
