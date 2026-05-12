# Regional Urban-Tier Tree Full Coverage v2 Report

This artifact defines auditable assignment coverage for all province-city pairs in the current admissions snapshot. It does not claim that every city-tier semantic boundary has been manually verified.

## Summary

| Metric | Value |
|---|---:|
| `total_city_pairs` | 414 |
| `total_schools` | 3,219 |
| `province_count` | 35 |
| `province_mapped_count` | 35 |
| `urban_city_pair_mapped_count` | 414 |
| `urban_city_pair_high_confidence_count` | 62 |
| `review_queue_count` | 0 |
| `remaining_unassigned` | 0 |

## Assignment Stats

| Source | Count |
|---|---:|
| `existing_seed` | 67 |
| `packet_suggested` | 347 |

| Item | Value |
|---|---:|
| Added nodes | 347 |
| Existing nodes | 70 |
| Final nodes | 417 |

## Final Coverage

| Item | Value |
|---|---:|
| Assigned distinct names | 414 |
| Assigned row count | 3,219 |
| Remaining unassigned distinct names | 0 |
| Remaining unassigned row count | 0 |

## Boundary

- The tree provides auditable coverage for the current snapshot.
- It does not encode city benefit or Pareto gain.
- The `reviewed_v1` tree remains as historical seed material.
