"""
stego_cli.py - NEW: command-line access to every feature (no GUI needed).

  python stego_cli.py capacity  cover.png
  python stego_cli.py encode    cover.png out.png --text "secret" [--password P] [--random]
  python stego_cli.py encode    cover.png out.png --file report.pdf --password P --random
  python stego_cli.py decode    out.png [--password P] [--save-to folder]
  python stego_cli.py detect    out.png
  python stego_cli.py compare   cover.png out.png [--diff diff.png]
"""
import argparse
import os
import sys

import steg_analysis as sa
import steg_core as sc
from hide_message import _read_image_array


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("capacity"); p.add_argument("image")
    p = sub.add_parser("encode"); p.add_argument("image"); p.add_argument("out")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--text"); g.add_argument("--file")
    p.add_argument("--password"); p.add_argument("--random", action="store_true")
    p = sub.add_parser("decode"); p.add_argument("image"); p.add_argument("--password"); p.add_argument("--save-to", default=".")
    p = sub.add_parser("detect"); p.add_argument("image")
    p = sub.add_parser("compare"); p.add_argument("cover"); p.add_argument("stego"); p.add_argument("--diff")
    a = ap.parse_args()

    try:
        if a.cmd == "capacity":
            result = sc.image_capacity(a.image)
            if result is None:
                raise sc.StegoError(f"Could not open image: {a.image}")
            w, h, cap = result
            print(f"{w}x{h} px  ->  up to {cap} text bytes (~{cap} ASCII characters), "
                  f"file payload up to ~{cap - 15} bytes")
        elif a.cmd == "encode":
            out = os.path.splitext(a.out)[0] + ".png"
            r = (sc.encode_text(a.image, a.text, out, a.password, a.random) if a.text is not None
                 else sc.encode_file(a.image, a.file, out, a.password, a.random))
            m = r.metrics
            print(f"Saved {out}  [{r.mode}]  {r.bits_used}/{r.capacity_bits} bits "
                  f"({100 * r.bits_used / r.capacity_bits:.2f}%)")
            print(f"MSE {m['mse']:.6f} | PSNR {m['psnr']:.2f} dB | SSIM {m['ssim']:.6f} | "
                  f"samples changed {m['samples_changed']}")
        elif a.cmd == "decode":
            r = sc.decode(a.image, a.password)
            if r.kind == "text":
                print(r.text)
            else:
                os.makedirs(a.save_to, exist_ok=True)
                dest = os.path.join(a.save_to, r.filename)
                with open(dest, "wb") as f:
                    f.write(r.data)
                print(f"Hidden file extracted -> {dest} ({len(r.data)} bytes)")
        elif a.cmd == "detect":
            print(sa.format_report(os.path.basename(a.image), sa.analyze_file(a.image)))
        elif a.cmd == "compare":
            c, s = _read_image_array(a.cover), _read_image_array(a.stego)
            if c is None or s is None or c.shape != s.shape:
                sys.exit("Images must exist and have the same size.")
            m = sc.compare_images(c, s)
            print(f"MSE {m['mse']:.6f} | PSNR {m['psnr']:.2f} dB | SSIM {m['ssim']:.6f} | "
                  f"samples changed {m['samples_changed']}/{m['samples_total']}")
            if a.diff:
                sc.density_preview(sc.difference_mask(c, s), 800, 800).save(a.diff)
                print("Difference map saved ->", a.diff)
    except (sc.StegoError, FileNotFoundError, OSError) as e:
        sys.exit(f"Error: {e}")


if __name__ == "__main__":
    main()
