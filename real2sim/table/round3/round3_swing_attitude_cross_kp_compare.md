# Swing Attitude Cross-Kp Compare

- Scope: first 4 touchdown-aligned swing phases only
- Airborne window rule: touchdown前 `0.35s` 到 `0.02s`，优先使用 `rel_height >= 0.02 m` 的腾空行

## baseline_35_0p5

- Touchdowns analyzed: `4`
- Mean abs sole roll during swing: `0.2782` rad
- Mean abs sole pitch during swing: `0.2819` rad
- Mean max abs sole roll during swing: `0.4076` rad
- Mean max abs sole pitch during swing: `0.4167` rad
- Mean roll at -50 ms: `-0.0333` rad
- Mean pitch at -50 ms: `0.3995` rad
- Mean roll at touchdown: `0.0593` rad
- Mean pitch at touchdown: `0.2245` rad
- Touchdown roll sign counts: `{'positive': 3, 'negative': 1}`

### left

- Mean abs swing roll: `0.2603` rad
- Mean abs swing pitch: `0.2177` rad
- Mean peak-clearance roll: `0.3526` rad
- Mean peak-clearance pitch: `0.1172` rad
- Mean roll at -20 ms: `0.0957` rad
- Mean pitch at -20 ms: `0.3035` rad

### right

- Mean abs swing roll: `0.2960` rad
- Mean abs swing pitch: `0.3460` rad
- Mean peak-clearance roll: `-0.4048` rad
- Mean peak-clearance pitch: `0.2792` rad
- Mean roll at -20 ms: `0.0169` rad
- Mean pitch at -20 ms: `0.2858` rad

### Mid-Swing Snapshot

- `left` phase `0.50`: roll `0.3764` rad, pitch `0.1589` rad, rel_height `0.0814` m
- `right` phase `0.50`: roll `-0.4175` rad, pitch `0.2730` rad, rel_height `0.1017` m

## high_kp_right_roll_50_0p8

- Touchdowns analyzed: `4`
- Mean abs sole roll during swing: `0.2571` rad
- Mean abs sole pitch during swing: `0.1668` rad
- Mean max abs sole roll during swing: `0.3851` rad
- Mean max abs sole pitch during swing: `0.3039` rad
- Mean roll at -50 ms: `-0.0702` rad
- Mean pitch at -50 ms: `0.1421` rad
- Mean roll at touchdown: `0.0846` rad
- Mean pitch at touchdown: `-0.1123` rad
- Touchdown roll sign counts: `{'positive': 4}`

### left

- Mean abs swing roll: `0.2671` rad
- Mean abs swing pitch: `0.1957` rad
- Mean peak-clearance roll: `0.3506` rad
- Mean peak-clearance pitch: `-0.2345` rad
- Mean roll at -20 ms: `-0.0162` rad
- Mean pitch at -20 ms: `-0.0826` rad

### right

- Mean abs swing roll: `0.2472` rad
- Mean abs swing pitch: `0.1380` rad
- Mean peak-clearance roll: `-0.3788` rad
- Mean peak-clearance pitch: `0.1663` rad
- Mean roll at -20 ms: `0.0937` rad
- Mean pitch at -20 ms: `0.0292` rad

### Mid-Swing Snapshot

- `left` phase `0.50`: roll `0.3612` rad, pitch `-0.1969` rad, rel_height `0.0827` m
- `right` phase `0.50`: roll `-0.3527` rad, pitch `0.1178` rad, rel_height `0.0924` m

## low_kp_right_roll_25_0p5

- Touchdowns analyzed: `4`
- Mean abs sole roll during swing: `0.2058` rad
- Mean abs sole pitch during swing: `0.0861` rad
- Mean max abs sole roll during swing: `0.3034` rad
- Mean max abs sole pitch during swing: `0.1549` rad
- Mean roll at -50 ms: `0.0227` rad
- Mean pitch at -50 ms: `-0.0372` rad
- Mean roll at touchdown: `-0.0235` rad
- Mean pitch at touchdown: `-0.0512` rad
- Touchdown roll sign counts: `{'positive': 2, 'negative': 2}`

### left

- Mean abs swing roll: `0.1979` rad
- Mean abs swing pitch: `0.1392` rad
- Mean peak-clearance roll: `0.2513` rad
- Mean peak-clearance pitch: `-0.1987` rad
- Mean roll at -20 ms: `-0.0992` rad
- Mean pitch at -20 ms: `-0.0221` rad

### right

- Mean abs swing roll: `0.2138` rad
- Mean abs swing pitch: `0.0329` rad
- Mean peak-clearance roll: `-0.3003` rad
- Mean peak-clearance pitch: `0.0138` rad
- Mean roll at -20 ms: `0.0962` rad
- Mean pitch at -20 ms: `-0.0177` rad

### Mid-Swing Snapshot

- `left` phase `0.50`: roll `0.2682` rad, pitch `-0.1722` rad, rel_height `0.0906` m
- `right` phase `0.50`: roll `-0.3003` rad, pitch `0.0150` rad, rel_height `0.0783` m

## low_kp_all_ankles_25_0p5

- Touchdowns analyzed: `4`
- Mean abs sole roll during swing: `0.2781` rad
- Mean abs sole pitch during swing: `0.0381` rad
- Mean max abs sole roll during swing: `0.4191` rad
- Mean max abs sole pitch during swing: `0.0871` rad
- Mean roll at -50 ms: `0.1288` rad
- Mean pitch at -50 ms: `0.0266` rad
- Mean roll at touchdown: `-0.0219` rad
- Mean pitch at touchdown: `0.0264` rad
- Touchdown roll sign counts: `{'negative': 3, 'positive': 1}`

### left

- Mean abs swing roll: `0.3054` rad
- Mean abs swing pitch: `0.0395` rad
- Mean peak-clearance roll: `0.4346` rad
- Mean peak-clearance pitch: `-0.0438` rad
- Mean roll at -20 ms: `-0.0977` rad
- Mean pitch at -20 ms: `0.0430` rad

### right

- Mean abs swing roll: `0.2508` rad
- Mean abs swing pitch: `0.0367` rad
- Mean peak-clearance roll: `-0.3763` rad
- Mean peak-clearance pitch: `-0.0001` rad
- Mean roll at -20 ms: `0.0793` rad
- Mean pitch at -20 ms: `0.0000` rad

### Mid-Swing Snapshot

- `left` phase `0.50`: roll `0.4356` rad, pitch `-0.0392` rad, rel_height `0.0895` m
- `right` phase `0.50`: roll `-0.3852` rad, pitch `-0.0019` rad, rel_height `0.0902` m

