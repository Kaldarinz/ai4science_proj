# Paper references

Working registry for the manuscript. Every row below was checked against a
Crossref record for the DOI in column 2 and, where a local PDF is named, read
in full text at the stated page. No row is metadata-only.

Use the same key in `paper/paper.tex` (both `\cite` and `\bibitem`). The
self-check `checks/check_paper.py` requires 5–10 cited keys, each registered
here with a bare DOI or OpenAlex ID in column 2.

| Key | DOI or OpenAlex ID | Evidence source and location | What it supports | Difference from this work |
| --- | --- | --- | --- | --- |
| zhang2017 | 10.1021/acs.chemrev.6b00468 | data/articles/zhang2017.pdf, all 114 PDF pages (printed pp. 3990–4103) read in consecutive batches; no unreadable page. Page-level findings in the section below: p. 23 (§3.1) on the unresolved size–fluence direction, p. 22 (§3) on the missing size model, pp. 9–10 (§2.1.1) on what "high temperature and high pressure" actually describes, p. 86 (§8) on the missing <100 ns to µs link. | Background for the introduction and discussion only. The review itself states that the LAL size–fluence direction cannot be identified while in situ LFL is present and that single-pulse fluence studies are needed (p. 23); that no model links material and liquid properties to the LAL primary particle diameter (p. 22); and that the extreme-conditions label applies to the plasma, not to the cavitation bubble where the particles reside (pp. 9–10). | A review of the whole LSPC field, not a corpus article: no claim-level counts and no per-article test of a claim against that article's own series. Citing it does not add an article to the 41-article corpus. |
| alkattan2018 | 10.3390/ijms19061563 | data/articles/80134/10.3390_ijms19061563.pdf, p.4 (Section 2), full text read. | The ablation mechanism is "a complex process involving extreme phenomena (shock wave, plasma plume and cavitation bubble, etc.) under severe physical and thermodynamic conditions (thousands of kelvins and hundreds of pascals)", all within "a few ns", and depends on pulse length, wavelength and fluence. Size dispersion is "broadened" with "polymodal size populations", and the sequence of mechanisms is called "a debated scenario". | A focused review of the authors' own Au and Si work with a biomedical emphasis, not a systematic survey. It asserts complexity but reports no claim-level statistics and no trend direction for gold size versus fluence. |
| kabashin2003 | 10.1063/1.1626793 | data/articles/535841/10.1063_1.1626793.pdf, p.3 (TEM result) and abstract. Conditions: 110 fs, 800 nm, 1 kHz, deionized water, F = 60–1000 J/cm2. | Size increases with fluence. Two ablation mechanisms are distinguished: thermal-free femtosecond ablation at F < 400 J/cm2 gives 3–10 nm quasi-monodisperse colloids, while plasma-induced heating at high fluence gives larger particles and a broad distribution. | One article, one setup, one material. This work does not re-measure it; it records the article's claim and tests it against the article's own series, and counts it in an article-level denominator. |
| tarasenko2006 | 10.1016/j.apsusc.2005.07.150 | data/articles/538022/10.1016_j.apsusc.2005.07.150.pdf, p.4. Conditions: 10 ns, 10 Hz, 532 nm, 10–250 J/cm2; TEM comparison at 95 and 160 J/cm2. | The opposite direction under nanosecond pulses: the average diameter decreases to 5–10 nm and the distribution narrows as fluence rises to 160 J/cm2. | Cited as a counter-example to a single trend direction, not as a refutation of kabashin2003. The two differ in pulse duration, wavelength and fluence range, which this work does not attempt to disentangle. |
| elsayed2013 | 10.1016/j.optlastec.2012.06.004 | data/articles/538366/10.1016_j.optlastec.2012.06.004.pdf, p.3 (7–35 J/cm2), p.4 (53–88 J/cm2), p.8 (40% ethanol). Conditions: 10 ns, 20 Hz, 1064 nm. | Non-monotonic behaviour inside one article: the average size decreases with fluence up to a critical value near 35 J/cm2 and then increases, and the critical fluence shifts with the liquid medium. | This work keeps the non-monotonic direction as a separate category rather than collapsing it into increase or decrease, and treats the medium shift as a qualified condition rather than a controlled variable. |
| nikolov2011 | 10.1016/j.apsusc.2010.10.146 | data/articles/537995/10.1016_j.apsusc.2010.10.146.pdf, p.4 (1064 nm, 5.8 and 15.5 J/cm2) and p.5 (532 nm, 5.3 and 19.9 J/cm2). Conditions: 15 ns, 10 Hz, Ag and Au in double-distilled water. | The direction depends on wavelength within one article: size is "practically independent" of fluence at the fundamental wavelength but increases strongly at the second harmonic. | This work records the two wavelengths as separate claims and excludes the cross-wavelength pairs from matching, because a claim naming one wavelength cannot be tested by the series of the other. |
| baimler2026 | 10.3390/nano16020079 | data/articles/544838/10.3390_nano16020079.pdf, p.9 and abstract. Conditions: 4 ns, 1 kHz, 1064 nm, pulse energy 4–57 uJ (12–181 mJ/cm2), 8 min irradiation of a nanochain colloid. | Pulse energy is non-monotonic: size grows with energy up to a fragmentation threshold (321 mJ/cm2 in the abstract), beyond which fragmentation dominates. | This work treats pulse energy as a distinct variable from fluence and does not convert between them, since the article reports energy and spot-dependent fluence separately. |
| ivanov2024 | 10.1016/j.apsusc.2023.158662 | data/articles/80079/10.1016_j.apsusc.2023.158662.pdf, p.6 (lattice temperature near 6500 K, "strong temperature and pressure gradients"), p.7 (the two energy-dissipation regimes "are not well-separated"), p.8 (Conclusions). | What a current model can and cannot do. A molecular-dynamics two-temperature model reproduces the qualitative size distribution and the effect of pulse-overlap-induced porosity, but the authors state that "due to the model limitations, however, we could not take into account the evolution of NPs' parameters on microsecond time scale", and that the regimes are not separable into a "rule of thumb". | One model family, one material, one geometry. This work does not model anything; it uses the paper only to bound what a predictive claim could rest on, and does not generalize from it to "existing models" as a class. |
| letzel2018 | 10.1016/j.apsusc.2017.11.130 | data/articles/537774/10.1016_j.apsusc.2017.11.130.pdf, p.1 (abstract). Five methods: STEM, SAXS, analytical disc centrifugation, DLS, UV-vis with Mie-Gans theory. | Measured size distributions are not directly comparable: the radius may be sphere-equivalent, hydrodynamic, Feret or radius of gyration, weighting differs, and "frequently reported small size shifts of the primary particle mode around 10 nm" need a significance test tied to the analytical method. | This work inherits the problem rather than solving it: it records the size statistic each article reports and applies two error rules, and it does not claim that a reported shift is physically real. |

## zhang2017 — full-text reading record

Read in full: `data/articles/zhang2017.pdf`, 114 PDF pages = printed
pp. 3990–4103, in consecutive batches of 3–6 pages. Every section was read,
including §§1–8 and the reference list (pp. 87–114, refs 1–1030). No page was
unreadable: every page returned extractable text, the minimum being about
1.5 kchar on the figure-heavy p. 73. Tables 6 (p. 72) and 7 (p. 83) extract as
garbled cell text; their captions and the surrounding prose are legible, and
no finding below rests on a table cell alone.

This is a review of the whole field (LAL, LFL, LML), not a corpus article. It
is background for the introduction and discussion. Citing it does not add an
article to the 41-article corpus, and it contributes no claim-level count.

Attribution convention: **[review]** marks the authors' own synthesis or their
explicit statement about the state of the field; **[primary, ref N]** marks a
result the review attributes to a cited primary study, with the review's own
reference number so the primary source can be checked directly.

### What researchers can control

Z1. **[review]** The adjustable set is enumerated as processing parameters
(bulk target, solvent and solutes, system temperature and pressure) and laser
parameters (wavelength, pulse duration, pulse energy, repetition rate, number
of pulses), which together give "a library of NMs covering nearly the entire
periodic table" (p. 3, §1.1). Typical LAL window: fluence ≈0.1–100 J/cm2,
pulse duration fs to CW (p. 5, §2.1).
→ Supports the versatility premise of `research/problem.md` (target, liquid,
laser parameters and focusing can be varied). It does not support unrestricted
versatility: the same review's size map still has blank ranges (Z21).

Z2. **[review]** The determinants are presented as synergistic rather than
independent: material properties, liquid parameters, laser parameters and
process adjustment, "with each determinant including several branching
factors" (p. 34, §5, Figure 37).
→ Supports "many coupled parameters".

Z3. **[review]** "although one laser system offers multiple size-affecting
parameters, the existence of mutual cross-effects between these parameters
makes it difficult to develop a general concept" (p. 24, §3.1).
→ Supports the "flexibility makes outcomes difficult to predict" premise, but
as a statement about coupled parameters, not as a measured prediction error.

Z4. **[review]** §3.1 closes by recommending "further investigation ... to
elucidate the impact of each parameter on NP nucleation and growth while
keeping all other parameters constant" (p. 24), and §8 asks for "well-defined
single-pulse experiments" to support the mechanism of LAL and LFL (p. 86).
→ Directly supports the manuscript's design choice of reading single-parameter
size-versus-fluence or size-versus-energy series, and supports describing the
gap as one the field itself names.

### Gold particle size versus fluence or pulse energy

Z5. **[primary, refs 84, 316, 194, 314]** "high-energy laser pulses have often
been reported to favor the formation of larger NPs, at least in terms of the
diameter of the modes in the number-weighted size histogram (Figure 28a,b)"
(p. 23, §3.1). Figure 28b is the Au two-mode mean size versus fluence for an
fs laser (ref 194).
→ This is the "increase" direction, and it is attributed, not asserted by the
review. Note the qualifier: the direction is stated for a mode diameter in a
number-weighted histogram, not for a mass- or volume-weighted mean.

Z6. **[primary, refs 84, 318, 306, 140, 319, 194, 305]** "Reduced laser energy
has been reported to decrease both the size and the size distribution of
LAL-synthesized particles ... independent of the laser pulse duration (e.g.,
fs, ns, and CW) and for various materials (e.g., Si, C, Au, and Ag)" (p. 23).
→ Same direction as Z5, restated as a cross-material regularity.

Z7. **[primary, refs 321, 322]** "the opposite effect has been reported as
well, where increasing the laser pulse fluence narrows the size distribution
of the generated NPs and results in smaller particles" (p. 23).
→ The review records both directions in the same paragraph. This is the
strongest single support for the manuscript's statement that the literature
reports different directions; it is a qualitative statement, not a count.

Z8. **[review]** The review's own explanation of that contradiction: "These
contradictory findings originate from the fact that it is difficult to exclude
in situ LFL of the NPs resulting from the energy absorption by NPs during
long-term LAL", together with pulse-number incubation and screening effects
and focus-position modulation of the fluence; hence "clearly identifying the
impact of laser fluence on NP size control during LAL remains difficult.
Elucidating the influence of laser fluence on LAL requires excluding LFL
effects; thus, SP-LAL fluence studies are needed" (p. 23, §3.1).
→ The central finding for the manuscript. It supports (a) treating a reported
size–fluence direction as a property of a particular experiment rather than of
the material, and (b) the framing that the trend is not predictable from the
named quantities alone. It also supplies the mechanism of the confound: in a
batch LAL experiment the colloid is re-irradiated, so the measured size mixes
ablation and fragmentation.

Z9. **[review]** The same confound is stated for wavelength: NPs made at
longer wavelengths are larger, "however, this size reduction is most likely
caused by LFL, is inevitable in LAL batch processes, and is usually amplified
by shorter wavelengths" (p. 57, §5.4.2). Likewise a thicker liquid layer "may
indirectly decrease the particle diameter" by enlarging the LFL volume, and
"interpretations of the effects of the liquid level reported in the literature
should consider this effect" (p. 50, §5.3.4).
→ Qualifies any reading of a size–fluence series as a pure ablation result,
and supports recording the reported size statistic and conditions rather than
interpreting the series physically.

Z10. **[review]** For LFL the direction is stated without hedging: "the higher
is the laser fluence and the longer is the irradiation period, the smaller the
particles will be" (p. 13, §2.2); **[primary, ref 232]** ns LFL of Au NPs from
88 to 442 mJ/cm2 decreased the average diameter from 24 to 4.6 nm.
→ Boundary condition: the decreasing direction belongs to fragmentation, not
to ablation. A sentence saying "size decreases with fluence" without naming
the process would be wrong for LAL and right for LFL.

Z11. **[review]** For LML the direction is increasing: "increasing the laser
fluence leads to a gradual increase in the particle size" (p. 21, §3);
**[primary, ref 272]** CuO submicrometer spheres grow from 260 to 370 nm
between 50 and 200 mJ/cm2, and above the LFL threshold collapse below 10 nm.
§5.4.3 summarises: "higher laser fluence values result in higher NP
productivity for LAL and larger SMS by LML" (p. 58).
→ Note what that sentence does not say: for LAL it claims productivity, not
primary particle size. The review nowhere states a single LAL size–fluence
law. This is the correct citation for "fluence controls yield" and it must not
be cited for "fluence controls size".

Z12. **[primary, ref 194]** Kabashin and Meunier: thermal-free fs ablation of
gold in water gives 3–10 nm colloids at low fluence, while at F > 400 J/cm2
"plasma-induced heating and ablation are triggered and result in a bimodal
particle size distribution" (p. 54, §5.4.1).
→ The review's version of the `kabashin2003` row above, and a check that the
two readings agree. It also shows the review reporting a threshold, not a
monotonic law.

Z13. **[review]** Repetition rate: increasing it increased Ag NP size in one
study and reduced Au NP size in fs LAL through the lower pulse energy, so "an
optimal repetition rate is expected to exist for each
intensity−liquid−material system" (p. 61, §5.4.5).
→ Supports keeping repetition rate as a condition to record rather than a
controlled variable, and warns against pooling series across repetition rates.

### Mechanisms and models: what is explained, what is left open

Z14. **[review]** The "high temperature and high pressure" label is corrected:
it "is closely related to the initial plasma state rather than the cavitation
bubble, although the NPs are located inside the 'cold' cavitation bubble vapor
most of the time" (p. 9, §2.1.1); the label "is only applicable to the initial
plasma and final collapse phases", and "this potentially misleading simplified
terminology should not be used to describe particle formation because the
temperature and pressure oscillate over several orders of magnitude in the gas
phase" (p. 10).
→ Qualifies the transient-conditions sentence in `research/problem.md`. The
manuscript may say the process passes through extreme states; it should not
say particles form under sustained high temperature and pressure. This is a
more specific statement than the one currently drawn from `alkattan2018` p. 4.

Z15. **[primary, refs 147, 153, 143]** Plasma: intensity >1e9 W/cm2, initial
density about 1e20 cm−3, lifetime tens of ns to a few µs (p. 6);
**[primary, refs 129, 143, 180, 181]** only the initial and collapse moments
are "hot" (>1000 K), while the expanding bubble is at hundreds of kelvins
(p. 9, Figure 10c); the Rayleigh–Plesset treatment ignores liquid
compressibility and fails after the first collapse, so the Gilmore model may
be preferable (p. 9).
→ Supports "steep gradients and rapidly varying conditions" and shows that the
model hierarchy itself is contested.

Z16. **[review]** Particle formation: cluster condensation from the vapour is
a candidate main mechanism (MD, ref 163); **[primary, ref 168]** smaller
particles form in the liquid–gas region and larger ones in the molten layer,
both depending on fluence (Figure 13a); **[primary, ref 163]** a trimodal
distribution (atom clusters 1–2 nm, NPs, droplets of tens of nm) is predicted
within <3 ns (Figure 13c). **[review]** "The formation of primary and
secondary NPs (a bimodal size distribution, which is often found after
performing LAL) is not fully understood" (p. 10, §2.1.2), and "a missing link
related to the structure and composition of the NPs found outside the bubble
in the free liquid remains" (p. 10).
→ Supports the statement that a reported size is a mixture of populations and
that bimodality is expected rather than anomalous.

Z17. **[review]** "no theoretical model has yet been constructed to correlate
the material and liquid properties with the primary particle diameter
resulting from LAL", and there is a "current inability to quantitatively
predict the NP size solely on the basis of the physicochemical properties of
the solid and liquid" (p. 22, §3).
→ The strongest available support for a prediction-gap statement, and narrower
than "models cannot predict size": it concerns predicting the primary particle
diameter from material and liquid properties.

Z18. **[review]** "There is no LAL productivity model until now that takes
parameters of the liquid into account, such as specific heat, permittivity, or
compressibility" (p. 28, §4.1).
→ A second, independent gap statement, about yield rather than size. Useful
because it does not depend on the size-measurement argument.

Z19. **[review]** "Substantial theoretical links between the early NP
generation phase (<100 ns) and the subsequent phase in the cavitation bubble
(∼µs) are still missing"; better understanding is needed "to predict the
oxidation or carbonization ratio of the products"; and the LFL bubble model
has not been extended "to a comprehensive model of NP fragmentation" (p. 86,
§8).
→ Supports describing the gap as a missing link between time scales, which is
compatible with the stated microsecond limitation of `ivanov2024` and does not
generalise to "no theory exists".

Z20. **[review]** "the extent to which NP formation is kinetically or
thermodynamically controlled remains unclear" (p. 34, §5.1.1); "the mechanisms
by which nuclei evolve into particles and different structures remain under
debate", and "it still lacks strong evidence indicating where and when the
reactions occur" (p. 11, §2.1.3).
→ Supports "the mechanism is debated" without asserting that no mechanism has
been proposed.

Z21. **[review]** Size control is bounded in practice: "monomodal and
monodisperse colloids are challenging to produce by LAL without compromising
colloidal purity. Even LAL at very low fluence (resulting in low throughput)
produces a secondary size mode" (p. 21, §3); "monomodal colloidal particles
remain difficult to obtain practically by varying the laser parameters during
LAL" (p. 11, §2.1.2); and "medium-sized monodisperse NPs ... such as 50 nm Au
NPs are still difficult to obtain" (p. 86, §8).
→ Qualifies any implication that varying the laser parameters alone delivers a
chosen size, and supports caution when comparing reported sizes across
articles.

### What this review does not license

- It is not a corpus statistic. It reports no count of articles by trend
  direction and no test of a claim against the same article's series. The
  manuscript's counts must come from `results/summary.json`.
- It does not state a general LAL size–fluence law in either direction. The
  only unhedged direction statements are for LFL (decreasing, Z10) and LML
  (increasing, Z11).
- It does not support "no theory exists" (Z15–Z20 all name models), and it does
  not support "existing models cannot predict particle size" without the
  qualifier in Z17.
- Its "hundreds of pascals" for the plasma (p. 7, §2.1.1) is the same
  implausible value that `alkattan2018` p. 4 repeats. The review is the likely
  proximate source of that wording, so the two are not independent witnesses
  for the number; see open item 3.
- Its reference list (p. 87 = printed 4076) confirms the bibliographic record
  of the candidate tenth reference in open item 2: ref 32 is Amendola and
  Meneghetti, Phys. Chem. Chem. Phys. 15 (2013) 3027–3046. That is a metadata
  cross-check only; the paper itself was still not read here.

## Coverage by requested category

- Field review: `zhang2017` (full text, all 114 pages) and `alkattan2018`
  (full text). The first is a broad review of LAL, LFL and LML written from one
  group's perspective; the second is a focused review of the authors' own Au
  and Si work. Neither reports claim-level counts, so the pair supports
  background statements only and is not a systematic field survey.
- Primary studies of gold particle size versus pulse fluence or energy:
  `kabashin2003` (increase), `tarasenko2006` (decrease), `elsayed2013`
  (non-monotonic), `nikolov2011` (no effect at 1064 nm, increase at 532 nm),
  `baimler2026` (non-monotonic in pulse energy). All five are gold, all five
  are read in full text, and all five are already in the fixed corpus, so
  citing them does not change the corpus.
- What current models can and cannot predict: `ivanov2024` for the capability
  and the stated limitation of one model family, `zhang2017` p.22 for the
  missing material/liquid-to-diameter model and p.86 for the missing link
  between the <100 ns and µs stages, `alkattan2018` p.4 for the complexity of
  the process being modelled, `letzel2018` for the measurement side of the same
  problem.

## Narrative claims checked against the sources

Supported.

- Versatility of the method: target material, liquid, laser parameters and
  focusing conditions can be varied (`zhang2017` p.3, §1.1, which enumerates
  processing and laser parameters and the resulting "library of NMs";
  `alkattan2018` p.4; also 538584 p.2, which lists wavelength, pulse width,
  fluence, repetition rate, growth medium and chamber design).
- Transient conditions: high temperature and steep gradients
  (`alkattan2018` p.4, "thousands of kelvins"; `ivanov2024` p.6, lattice
  temperature near 6500 K and "strong temperature and pressure gradients").
  `zhang2017` pp.9–10 adds the necessary qualifier: the extreme-conditions
  label describes the initial plasma and the final collapse, not the cavitation
  bubble in which the particles reside, and the review calls the unqualified
  wording "potentially misleading" for particle formation.
- Theory exists and is being developed (`ivanov2024` throughout;
  `alkattan2018` p.4 refers to theoretical modelling of the mechanism;
  `zhang2017` pp.6, 9, 10, 22, 28 and 86 name specific models and their
  stated limits).

Partly supported, needs careful wording.

- "Flexibility makes outcomes difficult to predict across setups." The sources
  support the premises — many coupled parameters (`alkattan2018` p.4;
  `zhang2017` p.34, Figure 37, and p.24, "mutual cross-effects ... makes it
  difficult to develop a general concept"), regimes that cannot be separated
  (`ivanov2024` p.7), a model that stops at the microsecond scale
  (`ivanov2024` p.8), and a measured confound between ablation and in situ
  fragmentation (`zhang2017` p.23). No source measures cross-setup
  predictability. Write this as a statement about mechanism complexity, model
  scope and a known confound, not as a demonstrated fact about prediction
  error.
- "Different size measurements can yield different trends." `letzel2018` p.1
  supports method- and weighting-dependent diameters and the need for a
  significance test on ~10 nm shifts. It does not show that a change of method
  reverses a trend direction. The stronger version is unsupported.

Not supported, do not write.

- Unrestricted versatility. 538584 p.2 records that the method "has less
  flexibility in terms of shapes and sizes of NPs". `research/problem.md`
  already forbids this claim; the sources confirm the prohibition.
- "Existing models cannot predict particle size." `ivanov2024` p.8 reports
  qualitative agreement between simulation and measured distributions and
  calls the approach a step towards controllable synthesis. `zhang2017` p.22
  states the narrower gap: no model yet correlates material and liquid
  properties with the LAL primary particle diameter. The defensible statement
  is that one model family predicts early-stage ejection qualitatively and
  does not follow microsecond-scale evolution, and that no model yet maps
  material and liquid properties onto the primary particle diameter.
- "No theory exists." Contradicted by `ivanov2024`, by `alkattan2018` p.4 and
  by `zhang2017` pp.6, 9, 10, 22, 28 and 86, which name specific models and
  their limits.
- A general trend of gold size with fluence or pulse energy. The five primary
  studies give increase, decrease, non-monotonic and no-effect outcomes under
  different pulse durations, wavelengths and ranges. `zhang2017` p.23 records
  both directions in one paragraph and attributes the contradiction to
  inseparable in situ LFL, which supports the framing but is not a count. This
  heterogeneity is consistent with the paper's framing but is not a corpus
  statistic and must not be presented as one; the corpus counts come from
  `results/summary.json`.
- "Size decreases with fluence" as a general statement. `zhang2017` p.13 gives
  that direction for LFL and p.21 the opposite for LML; for LAL the review
  claims only that fluence raises productivity (p.58). Any such sentence must
  name the process.

## Open items for the curator

1. Resolved: `zhang2017` is no longer metadata-only. The PDF was supplied as
   `data/articles/zhang2017.pdf` and read in full (114 pages, no unreadable
   page); the table row and the reading record above now carry page-level
   findings. The key is usable as background for the introduction and
   discussion. It must not be cited for a corpus count, for a general LAL
   size–fluence direction, or for "no theory exists". No further action is
   needed unless the curator prefers to drop the key.
2. Candidate tenth reference, not registered: Amendola and Meneghetti,
   "What controls the composition and the structure of nanomaterials generated
   by laser ablation in liquid solution?", Phys. Chem. Chem. Phys. 15 (2013)
   3027–3046, DOI 10.1039/c2cp42895d. Crossref metadata verified; the full
   bibliographic record also appears as reference [10] of 538584 (p.2 and
   reference list), and the retained claim 537774-c1 attributes to it the
   statement that the minimum accessible particle diameter is a function of
   the applied fluence (per the extraction record, not re-read here). Full
   text was not accessible, so no finding is attributed. It is the natural
   source for the "what controls the size" framing if the curator can provide
   the PDF. The same bibliographic record is confirmed independently as ref 32
   of `zhang2017` (p.87 = printed 4076), which cites it for mechanistic
   scenarios and size manipulation; that is a metadata cross-check only.
3. `alkattan2018` p.4 states "hundreds of pascals" for the pressure of the
   ablation region, which is implausible for a plasma plume and is probably a
   unit error in the source. Quote it literally or avoid the number; do not
   propagate it as a physical value. `zhang2017` p.7 (§2.1.1) carries the same
   wording ("thousands of kelvins ... and hundreds of pascals"), so the two are
   not independent witnesses and the review is the likely proximate source.
   The implausibility is unchanged.
4. No key above is yet cited in `paper/paper.tex`; the manuscript still has no
   `\cite` or `\bibitem` entries. That is the next writing step, not part of
   this pass.
