# English 6.3.0 catalog — editorial audit

The English DLC reference recovered from the patch source contains two literal U+FFFD replacement characters. They are present in the reference extraction, not introduced by the HTML template.

| Quest | Source phrase | Corrected working-catalog phrase | Status |
|---|---|---|---|
| `m60024.mib` | `It�s tough` | `It's tough` | Editorial encoding repair |
| `m60021.mib` | `It�s a dream-come-true set!` | `It's a dream-come-true set!` | Editorial encoding repair |

The working catalog retains the original damaged phrase as a **legacy detection string**, not an output translation. This prevents a previously released English pilot or the patch reference from being mistaken for unknown custom text. The analyzer will label matching records `eligible_editorial_repair` without changing them.

The patch reference also includes `Island Egg Festival！` with fullwidth U+FF01; we kept it unchanged and marked it as a nonblocking style advisory because changing it is not required to resolve a text-decoding defect.

Do not normalize other monster nomenclature or punctuation without comparing with the actual patch resources and making an explicit editorial decision.

## v0.4 update

The original U+FF01 fullwidth exclamation in `m60029.mib` is approved text and is preserved exactly. The analyzer no longer reports this valid punctuation as a warning. The two documented U+FFFD repairs remain explicit editorial corrections, and all English output fields are checked for exact byte-for-byte UTF-8 roundtrips.

## v0.4.1: original name spacing and identity

`ｕｅ．` is three fullwidth characters, not six ASCII characters with spaces. Preserve the original name code points exactly for this promotional Palico. The current English nickname catalog entry is therefore `ｕｅ．`, not `ue.`; translate the comment independently. This corrects the unintended display-width loss of the previous catalog.


v0.5.1 adds separately selectable localization for previously recruited promotional copies. It does not change the actual translation catalog, which still preserves original fullwidth ｕｅ． and ｍａｋｉ. Recruited copies are only eligible if independently matched to the source and all text is approved/known.
