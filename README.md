# middle-key

**MIKE (Middle Key)** programmatically captures airband traffic. It listens to an airband
frequency with a software-defined radio (SDR), detects each transmission, and saves it as its own
WAV file, named with its UTC start time and frequency.

**Status: v0.1.0 (MVP).** One channel at a time, on an Ettus USRP B200-series radio (developed on
a B206mini).

## How It Works

```
SDR (wideband IQ, 240 kS/s)
 └─► Channelizer      shift the channel to 0 Hz, low-pass filter, decimate to ~48 kS/s
      └─► BurstDetector   squelch: compare power to an adaptive noise floor
           └─► BurstRecorder  keep samples; cut out each complete transmission
                └─► AM demodulation ─► normalization ─► WAV file
```

Only complete transmissions are saved: one still in progress when MIKE stops is discarded.

## Requirements

- Python 3.10 or later
- An Ettus USRP B200-series radio, with an antenna suited to the airband (118-137 MHz)
- UHD and its Python bindings. These come from your OS's packages, not PyPI. On Debian/Ubuntu:

  ```bash
  sudo apt install uhd-host python3-uhd
  sudo uhd_images_downloader   # FPGA images the B200 series loads at startup
  uhd_find_devices             # should list your radio
  ```

## Installation

```bash
git clone https://github.com/hark130/middle-key.git
cd middle-key
pip install -e .                      # MIKE itself
pip install -e ".[tools,test,lint]"   # plus the development extras
```

## Usage

```bash
mike --freq 119.8e6 --out data/saved
```

| Argument | Default | Meaning |
|---|---|---|
| `-f`, `--freq` | (required) | Channel frequency, in Hz (e.g., `119.8e6`) |
| `-g`, `--gain` | `40` | RF gain, in dB (B200 series: roughly 0-76) |
| `-o`, `--out` | current directory | Directory to save the WAV files in (must exist) |
| `-d`, `--debug` | off | Verbose logging, plus a live meter: channel power, noise floor, and squelch state |

`python -m middle_key` works the same as `mike`. Press **Ctrl+C** to stop.

Each transmission is printed as it's saved:

```
14:22:17Z  119.800 MHz    3.4 s  -> data/saved/20261102T142217.123Z_119800k.wav
```

### Output files

`YYYYMMDDTHHMMSS.mmmZ_<frequency in kHz>k.wav`: the UTC start time (to the millisecond) and
the channel frequency. Names sort chronologically. The files are 16-bit mono WAV, normalized
per transmission, so quiet aircraft play about as loud as nearby ones.

## Tuning

Squelch and recording settings live in `src/middle_key/constants.py` (the `BURST_*` constants).
With `--debug`, watch the meter while traffic is on the channel:

| Symptom | Adjust |
|---|---|
| One transmission is split into two files | Raise `BURST_HANG_S` |
| A controller and pilot's back-and-forth merge into one file | Lower `BURST_HANG_S` |
| Weak aircraft are missed | Lower `BURST_OPEN_DB` (keep `BURST_CLOSE_DB` at least 3 dB below it) |
| Noise or clicks get saved | Raise `BURST_OPEN_DB`, or lengthen `BURST_CONFIRM_S` |

Radio settings (sample rate, tuning offset, antenna) live in `src/middle_key/radio/constants.py`.

## Development

```bash
./scripts/run_linters.sh   # Pycodestyle and Pylint, using the settings in setup.cfg and pyproject.toml
```

Supporting a new SDR means writing an `Sdr` subclass in the `radio` sub-package: see
`src/middle_key/radio/sdr.py` (the interface) and `usrp_sdr.py` (an example), then register it in
`radio/factory.py`.

## Repo Hierarchy

```
middle-key/
├── data/            # captures and generated audio (git-ignored)
├── flowgraphs/      # GRC flowgraphs (.grc) used to make test captures
├── scripts/         # development scripts (e.g., run_linters.sh)
├── src/middle_key/  # the package
│   └── radio/       # SDR hardware abstraction layer: one Sdr subclass per radio family
├── tools/           # standalone helper scripts (inspect captures and WAV files)
├── test/            # unit tests (planned)
├── README.md
└── LICENSE
```

## Roadmap

- RTL-SDR and HackRF support
- Several channels at once (e.g., Tower, Ground, and Approach), with channel labels
- Live playback queue, showing each transmission's frequency as it plays
- Release as a wheel

## License

MIT: see [LICENSE](LICENSE).
