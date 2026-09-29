# __NAME__

| Document | Audience | Built by |
|---|---|---|
| `pdf/__SLUG___Guide.pdf` | you only | `src/build_guide.py` |
| `pdf/__SLUG___Party_Handout.pdf` | the party | `src/build_party_handout.py` |
| `pdf/__SLUG___DM_Brief.pdf` | the DM | `src/build_dm_brief.py` |

## Getting started

1. Set `dndbeyond_id` and `class_summary` in `character.yaml`, then
   `ddtools fetch __SLUG__` and `ddtools summary __SLUG__`.
2. Put every input (backstory, build notes, teammates) in `notes/sources/`, as received.
3. Fill in each section of the three scripts in `src/`, following the blueprints (`ddtools blueprints`).
4. Record choices and corrections in `notes/decisions.md`; secrets go in `secrets.txt`.
5. `ddtools build __SLUG__`, `ddtools check __SLUG__`, `ddtools preview __SLUG__`,
   then `ddtools golden update __SLUG__` and commit.
