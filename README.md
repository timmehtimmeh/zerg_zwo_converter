# Zerg zwo Converter
ERG/MRC to Zwift Workout File, based on code posted to this blog https://fukawitribe.wordpress.com/2015/12/15/zerg-ergmrc-to-zwift-workout-file/

# Usage

```
        zerg [options] file1.mrc [file2.mrc ...]

        Convert one or more ERG/MRC files to Zwift Workout (zwo) files.
        Currently only MRC files are supported (workouts are relative to
        FTP, effort is NOT defined in Watts).

        Options :

        -D <dir>  Place all converted files into directory <dir>.
                  Default is to write the converted data file to
                  the same directory as the original data file.

        -h        Help. Show this page and exit.

        -o <name> Save converted file to <name>. Default is to
                  name the converted data file the same as the
                  original data file except for the extension
                  which will be changed to '.zwo', e.g.

                       example.mrc -> example.zwo

                  This obviously only makes sense when one file
                  is being converted. No check is made that the
                  converted data file name is different from the
                  original data file name currently - beware.

        -m        Skip Course Text conversion.
```

For example:

```
python zerg.py path/to/workout.mrc
```

See also http://kb.zwiftriders.com/convert-sufferfest-to-Zwift

# ZWO Tag Syntax Documentation
In an effort to better understand the format that is needed for Zwift to correctly accept the files this script creates, here is some reverse engineered documentation.

## SteadyState
An interval that stays at the same level for the entire time.
  - Duration: Time of Interval, in seconds
  - PowerLow: % of FTP for interval divided by 100
  - PowerHigh: % of FTP for interval divided by 100 (appears to be redundant to PowerHigh)
  

## Warmup
An interval that slowly increases the power required throughout the duration of the interval.
  - Duration: Time of Interval, in seconds
  - PowerLow: % of FTP for the start of the warmup divided by 100
  - PowerHigh: % of FTP for the end of the warmup divided by 100

## Cooldown
An interval that slowly decreases the power required throughout the duration of the interval.
  - Duration: Time of Interval, in seconds
  - PowerLow: % of FTP for the start of the cooldown divided by 100
  - PowerHigh: % of FTP for the end of the cooldown divided by 100
****