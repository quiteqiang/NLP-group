# @title [RUN] Numbers quoted in the report
#
# Self-contained: references nothing from earlier cells, defines no globals
# that could clash, and trains nothing. Safe to run at any point.
#
# It reproduces the three report figures that are derived from results the
# notebook already printed, but that no single cell prints on its own:
#   (1) the pooled seed-noise standard deviation and the 2-sigma threshold
#   (2) the total parameter count of the full model
#   (3) the share of parameters held by the embedding matrix

def _report_numbers():
    import math

    line = "-" * 68

    # ================================================================
    # 1. SEED-NOISE FLOOR
    # ================================================================
    # Per-configuration standard deviations over seeds 0,1,2, copied from
    # the sweep tables printed by run_configurations() in Steps 11a-11d.
    # The base configuration appears in two sweeps with an identical sd;
    # it is listed once, giving 16 distinct configurations.
    sweep = [
        ("base (dim 100, hidden 100, 1 layer)", 0.6003, 0.0032),
        ("dropout 0.00",                        0.5780, 0.0024),
        ("dropout 0.10",                        0.5927, 0.0002),
        ("dropout 0.50",                        0.5921, 0.0024),
        ("lr 0.0003",                           0.5864, 0.0007),
        ("lr 0.0030",                           0.6041, 0.0083),
        ("lr 0.0100",                           0.6009, 0.0012),
        ("dimension 50",                        0.5876, 0.0081),
        ("dimension 200",                       0.5985, 0.0042),
        ("n_hidden 50",                         0.5952, 0.0076),
        ("n_hidden 200",                        0.5929, 0.0026),
        ("layers 2",                            0.5871, 0.0038),
        ("GRU (base is LSTM)",                  0.5922, 0.0060),
        ("max pooling (base is mean)",          0.5927, 0.0067),
        ("no interaction (400)",                0.5898, 0.0071),
        ("GOAL REMOVED (control)",              0.5854, 0.0015),
    ]

    sds = [s for _, _, s in sweep]
    n = len(sds)

    # Pooled sd across groups of equal size is the root mean square of the
    # per-group sds, not their arithmetic mean. The per-sweep figure printed
    # during the sweeps is the arithmetic mean, which is a different number.
    pooled = math.sqrt(sum(s * s for s in sds) / n)
    plain_mean = sum(sds) / n
    threshold = 2 * pooled

    print(line)
    print("1. SEED-NOISE FLOOR")
    print(line)
    print("  configurations                 %d" % n)
    print("  per-config sd ranges from      %.4f to %.4f" % (min(sds), max(sds)))
    print("  arithmetic mean of the sds     %.4f   (printed per sweep)" % plain_mean)
    print("  POOLED sd  = RMS of the sds    %.4f" % pooled)
    print("  THRESHOLD  = 2 x pooled sd     %.4f" % threshold)
    print()
    print("  Two configurations whose means differ by less than %.4f are" % threshold)
    print("  treated as indistinguishable; larger gaps are tested with Welch's t.")

    # ================================================================
    # 2. PARAMETER COUNT, FULL MODEL
    # ================================================================
    # Architecture constants as used for every reported run.
    V = 11488   # vocabulary size, already includes <pad> and <unk>
    d = 100     # embedding dimension
    H = 100     # hidden size per direction, so 2H = 200
    r = 64      # low-rank width of the goal-to-solution residual

    parts = [
        ("embedding  V x d",            V * d),
        ("Bi-LSTM, 1 layer",            2 * (4 * H * d + 4 * H * H + 4 * H + 4 * H)),
        ("W, A1 bilinear query",        (2 * H) * (2 * H)),
        ("pool_query, A1 self",         2 * H),
        ("goal_query, A2",              2 * H),
        ("W_Q/W_K/W_V/W_O, low rank",   3 * (2 * H) * r + r * (2 * H)),
        ("beta, temperature, gamma",    3),
        ("scorer 12H -> H",             (12 * H) * H + H),
        ("scorer H -> 1",               H + 1),
    ]
    total = sum(v for _, v in parts)
    embedding = parts[0][1]
    attention = parts[5][1] + parts[6][1]

    print()
    print(line)
    print("2. PARAMETER COUNT, FULL MODEL")
    print(line)
    for name, v in parts:
        print("  %-28s %11s" % (name, format(v, ",")))
    print("  %-28s %11s" % ("TOTAL", format(total, ",")))

    print()
    print(line)
    print("3. WHERE THE PARAMETERS SIT")
    print(line)
    print("  embedding matrix               %11s   %4.1f%%"
          % (format(embedding, ","), 100.0 * embedding / total))
    print("  low-rank attention refinement  %11s   %4.1f%%"
          % (format(attention, ","), 100.0 * attention / total))
    print()
    print("  Close to three quarters of what the model must learn is the word")
    print("  representations themselves, trained from scratch on 13,696 instances.")
    print(line)


_report_numbers()
