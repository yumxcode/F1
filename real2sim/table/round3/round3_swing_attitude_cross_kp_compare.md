# Swing Attitude Cross-Kp Compare

- Scope: first 4 touchdown-aligned swing phases only
- Airborne window rule: touchdown前 `0.35s` 到 `0.02s`，优先使用 `rel_height >= 0.02 m` 的腾空行

## baseline_35_0p5

- Touchdowns analyzed: `4`
- Mean abs sole roll during swing: `1.9148` rad
- Mean abs sole pitch during swing: `0.1222` rad
- Mean max abs sole roll during swing: `2.0421` rad
- Mean max abs sole pitch during swing: `0.2372` rad
- Mean roll at -50 ms: `-0.0427` rad
- Mean pitch at -50 ms: `-0.0144` rad
- Mean roll at touchdown: `0.0068` rad
- Mean pitch at touchdown: `-0.1090` rad
- Touchdown roll sign counts: `{'positive': 2, 'negative': 2}`

### left

- Mean abs swing roll: `1.8214` rad
- Mean abs swing pitch: `0.0968` rad
- Mean peak-clearance roll: `1.8959` rad
- Mean peak-clearance pitch: `-0.1106` rad
- Mean roll at -20 ms: `1.7334` rad
- Mean pitch at -20 ms: `-0.1103` rad

### right

- Mean abs swing roll: `2.0081` rad
- Mean abs swing pitch: `0.1476` rad
- Mean peak-clearance roll: `-2.1363` rad
- Mean peak-clearance pitch: `0.0529` rad
- Mean roll at -20 ms: `-1.7980` rad
- Mean pitch at -20 ms: `0.0780` rad

### Mid-Swing Snapshot

- `left` phase `0.50`: roll `1.8551` rad, pitch `-0.0687` rad, rel_height `0.0662` m
- `right` phase `0.50`: roll `-2.1002` rad, pitch `-0.2074` rad, rel_height `0.1092` m

## high_kp_right_roll_50_0p8

- Touchdowns analyzed: `4`
- Mean abs sole roll during swing: `1.8938` rad
- Mean abs sole pitch during swing: `0.2057` rad
- Mean max abs sole roll during swing: `1.9849` rad
- Mean max abs sole pitch during swing: `0.3527` rad
- Mean roll at -50 ms: `-0.1299` rad
- Mean pitch at -50 ms: `-0.2184` rad
- Mean roll at touchdown: `-0.1583` rad
- Mean pitch at touchdown: `-0.0785` rad
- Touchdown roll sign counts: `{'positive': 2, 'negative': 2}`

### left

- Mean abs swing roll: `1.8098` rad
- Mean abs swing pitch: `0.1367` rad
- Mean peak-clearance roll: `1.8564` rad
- Mean peak-clearance pitch: `-0.1378` rad
- Mean roll at -20 ms: `1.6510` rad
- Mean pitch at -20 ms: `-0.0617` rad

### right

- Mean abs swing roll: `1.9779` rad
- Mean abs swing pitch: `0.2746` rad
- Mean peak-clearance roll: `-2.1015` rad
- Mean peak-clearance pitch: `-0.0688` rad
- Mean roll at -20 ms: `-1.9896` rad
- Mean pitch at -20 ms: `-0.3917` rad

### Mid-Swing Snapshot

- `left` phase `0.50`: roll `1.8546` rad, pitch `-0.0866` rad, rel_height `0.0732` m
- `right` phase `0.50`: roll `-2.0290` rad, pitch `-0.0962` rad, rel_height `0.0682` m

## low_kp_right_roll_25_0p5

- Touchdowns analyzed: `4`
- Mean abs sole roll during swing: `1.7831` rad
- Mean abs sole pitch during swing: `0.0694` rad
- Mean max abs sole roll during swing: `1.8763` rad
- Mean max abs sole pitch during swing: `0.1191` rad
- Mean roll at -50 ms: `-0.0152` rad
- Mean pitch at -50 ms: `-0.1193` rad
- Mean roll at touchdown: `-0.0064` rad
- Mean pitch at touchdown: `-0.0929` rad
- Touchdown roll sign counts: `{'negative': 2, 'positive': 2}`

### left

- Mean abs swing roll: `1.7537` rad
- Mean abs swing pitch: `0.1046` rad
- Mean peak-clearance roll: `1.8174` rad
- Mean peak-clearance pitch: `-0.1061` rad
- Mean roll at -20 ms: `1.5592` rad
- Mean pitch at -20 ms: `-0.1308` rad

### right

- Mean abs swing roll: `1.8124` rad
- Mean abs swing pitch: `0.0342` rad
- Mean peak-clearance roll: `-1.9010` rad
- Mean peak-clearance pitch: `0.0024` rad
- Mean roll at -20 ms: `-1.5699` rad
- Mean pitch at -20 ms: `-0.0698` rad

### Mid-Swing Snapshot

- `left` phase `0.50`: roll `1.8081` rad, pitch `-0.0768` rad, rel_height `0.0815` m
- `right` phase `0.50`: roll `-1.8713` rad, pitch `0.0160` rad, rel_height `0.0765` m

## low_kp_all_ankles_25_0p5

- Touchdowns analyzed: `4`
- Mean abs sole roll during swing: `1.8832` rad
- Mean abs sole pitch during swing: `0.0489` rad
- Mean max abs sole roll during swing: `2.0187` rad
- Mean max abs sole pitch during swing: `0.0814` rad
- Mean roll at -50 ms: `0.1374` rad
- Mean pitch at -50 ms: `-0.0521` rad
- Mean roll at touchdown: `0.0653` rad
- Mean pitch at touchdown: `-0.0323` rad
- Touchdown roll sign counts: `{'positive': 2, 'negative': 2}`

### left

- Mean abs swing roll: `1.9577` rad
- Mean abs swing pitch: `0.0642` rad
- Mean peak-clearance roll: `2.0387` rad
- Mean peak-clearance pitch: `-0.0872` rad
- Mean roll at -20 ms: `1.9194` rad
- Mean pitch at -20 ms: `-0.0855` rad

### right

- Mean abs swing roll: `1.8086` rad
- Mean abs swing pitch: `0.0335` rad
- Mean peak-clearance roll: `-1.9772` rad
- Mean peak-clearance pitch: `-0.0139` rad
- Mean roll at -20 ms: `-1.6550` rad
- Mean pitch at -20 ms: `-0.0059` rad

### Mid-Swing Snapshot

- `left` phase `0.50`: roll `2.0209` rad, pitch `-0.0667` rad, rel_height `0.0782` m
- `right` phase `0.50`: roll `-1.8780` rad, pitch `-0.0061` rad, rel_height `0.0742` m

