import cv2
import numpy as np
from pathlib import Path
import glob

DESKTOP = Path("/Users/mohaned.saleh/Desktop")
files = sorted(glob.glob(str(DESKTOP / "Screenshot 2026-04-16 at 4.1[567]*.png")))

images = []
for i, f in enumerate(files):
    images.append(cv2.imread(f, cv2.IMREAD_COLOR))
    print(f"[{i}] {Path(f).name}  {images[-1].shape[1]}x{images[-1].shape[0]}")

LEFT_MASK = 80
MINIMAP_W = 440
MINIMAP_H = 440

def make_mask(shape):
    h, w = shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)
    mask[5:h - 30, LEFT_MASK:w - 10] = 255
    mask[h - MINIMAP_H:, w - MINIMAP_W:] = 0
    return mask


def find_translation(img_a, img_b):
    gray_a = cv2.cvtColor(img_a, cv2.COLOR_BGR2GRAY)
    gray_b = cv2.cvtColor(img_b, cv2.COLOR_BGR2GRAY)
    mask_a, mask_b = make_mask(img_a.shape), make_mask(img_b.shape)
    sift = cv2.SIFT_create(nfeatures=10000, contrastThreshold=0.03)
    kp_a, des_a = sift.detectAndCompute(gray_a, mask_a)
    kp_b, des_b = sift.detectAndCompute(gray_b, mask_b)
    if des_a is None or des_b is None or len(kp_a) < 10 or len(kp_b) < 10:
        return None
    flann = cv2.FlannBasedMatcher(dict(algorithm=1, trees=5), dict(checks=200))
    matches = flann.knnMatch(des_a, des_b, k=2)
    good = [m for m, n in (p for p in matches if len(p) == 2) if m.distance < 0.65 * n.distance]
    if len(good) < 10:
        return None
    pts_a = np.float32([kp_a[m.queryIdx].pt for m in good])
    pts_b = np.float32([kp_b[m.trainIdx].pt for m in good])
    deltas = pts_a - pts_b
    best_inliers, best_mask = 0, None
    rng = np.random.default_rng(42)
    for _ in range(2000):
        idx = rng.integers(0, len(deltas))
        errs = np.sqrt((deltas[:, 0] - deltas[idx, 0]) ** 2 + (deltas[:, 1] - deltas[idx, 1]) ** 2)
        m = errs < 4.0
        n_in = int(m.sum())
        if n_in > best_inliers:
            best_inliers = n_in
            best_mask = m.copy()
    if best_inliers < 20:
        return None
    inlier_deltas = deltas[best_mask]
    return (float(np.median(inlier_deltas[:, 0])),
            float(np.median(inlier_deltas[:, 1])),
            best_inliers)


def find_similarity(img_ref, img_src):
    gray_r = cv2.cvtColor(img_ref, cv2.COLOR_BGR2GRAY)
    gray_s = cv2.cvtColor(img_src, cv2.COLOR_BGR2GRAY)
    mask_r, mask_s = make_mask(img_ref.shape), make_mask(img_src.shape)
    sift = cv2.SIFT_create(nfeatures=12000, contrastThreshold=0.02)
    kp_r, des_r = sift.detectAndCompute(gray_r, mask_r)
    kp_s, des_s = sift.detectAndCompute(gray_s, mask_s)
    if des_r is None or des_s is None or len(kp_r) < 10 or len(kp_s) < 10:
        return None
    flann = cv2.FlannBasedMatcher(dict(algorithm=1, trees=5), dict(checks=300))
    matches = flann.knnMatch(des_r, des_s, k=2)
    good = [m for m, n in (p for p in matches if len(p) == 2) if m.distance < 0.7 * n.distance]
    if len(good) < 15:
        return None
    pts_r = np.float32([kp_r[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    pts_s = np.float32([kp_s[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
    M, inlier_mask = cv2.estimateAffinePartial2D(pts_s, pts_r, method=cv2.RANSAC, ransacReprojThreshold=5.0)
    if M is None:
        return None
    inliers = int(inlier_mask.sum())
    scale = np.sqrt(M[0, 0] ** 2 + M[1, 0] ** 2)
    if inliers < 15 or not (0.3 < scale < 3.0):
        return None
    return (M, scale, inliers)


# === Step 1: Place same-zoom images [2]-[7] ===
print("\n=== Step 1: Place [2]-[7] via translation ===")
use_idx = list(range(2, 8))
all_matches = {}
for ii in range(len(use_idx)):
    for jj in range(ii + 1, len(use_idx)):
        i, j = use_idx[ii], use_idx[jj]
        r = find_translation(images[i], images[j])
        if r:
            all_matches[(i, j)] = r
            print(f"  [{i}]→[{j}]: dx={r[0]:+.1f} dy={r[1]:+.1f} inliers={r[2]}")

positions = {2: (0.0, 0.0)}
changed = True
while changed:
    changed = False
    for (i, j), (dx, dy, inl) in sorted(all_matches.items(), key=lambda x: -x[1][2]):
        if i in positions and j not in positions:
            positions[j] = (positions[i][0] + dx, positions[i][1] + dy)
            changed = True
        elif j in positions and i not in positions:
            positions[i] = (positions[j][0] - dx, positions[j][1] - dy)
            changed = True

for i in sorted(positions):
    print(f"  [{i}] ({positions[i][0]:+.0f}, {positions[i][1]:+.0f})")

# === Step 2: Find similarity transforms for [0] and [1] ===
print("\n=== Step 2: Similarity transforms for [0],[1] ===")
warp_transforms = {}

for zi in [0, 1]:
    best = None
    for pi in sorted(positions):
        r = find_similarity(images[pi], images[zi])
        if r:
            M, scale, inl = r
            print(f"  [{pi}]←[{zi}]: scale={scale:.4f} inliers={inl}")
            if best is None or inl > best[0]:
                best = (inl, pi, M, scale)
    if best:
        inl, pi, M, scale = best
        # M maps [zi] pixels → [pi] pixels. Compose with [pi]'s canvas position.
        M_canvas = M.copy()
        M_canvas[0, 2] += positions[pi][0]
        M_canvas[1, 2] += positions[pi][1]
        warp_transforms[zi] = (M_canvas, scale, inl, pi)
        print(f"  → [{zi}] best via [{pi}], scale={scale:.4f}, {inl} inliers")

# === Step 3: Compute canvas bounds ===
print("\n=== Step 3: Compute canvas bounds ===")
all_corners = []
for i in sorted(positions):
    ox, oy = positions[i]
    h, w = images[i].shape[:2]
    all_corners.extend([(ox, oy), (ox + w, oy), (ox, oy + h), (ox + w, oy + h)])

for zi in warp_transforms:
    M_canvas = warp_transforms[zi][0]
    h, w = images[zi].shape[:2]
    corners = np.float32([[0, 0], [w, 0], [0, h], [w, h]])
    for pt in corners:
        cx = M_canvas[0, 0] * pt[0] + M_canvas[0, 1] * pt[1] + M_canvas[0, 2]
        cy = M_canvas[1, 0] * pt[0] + M_canvas[1, 1] * pt[1] + M_canvas[1, 2]
        all_corners.append((cx, cy))

min_x = min(c[0] for c in all_corners)
min_y = min(c[1] for c in all_corners)
max_x = max(c[0] for c in all_corners)
max_y = max(c[1] for c in all_corners)

# Upscale factor for higher res output
SCALE = 2
canvas_w = int(np.ceil((max_x - min_x) * SCALE)) + 1
canvas_h = int(np.ceil((max_y - min_y) * SCALE)) + 1
print(f"  Native: {int(max_x - min_x)}x{int(max_y - min_y)}")
print(f"  Output at {SCALE}x: {canvas_w}x{canvas_h}")

# === Step 4: Seam-based compositing ===
print("\n=== Step 4: Compositing ===")

# Prepare all tiles: each tile is (warped_image, coverage_mask, interior_distance_map)
tiles = []

# Translation-based images [2]-[7]: upscale by SCALE
for i in sorted(positions):
    ox = (positions[i][0] - min_x) * SCALE
    oy = (positions[i][1] - min_y) * SCALE
    h, w = images[i].shape[:2]
    img_up = cv2.resize(images[i], (w * SCALE, h * SCALE), interpolation=cv2.INTER_LANCZOS4)
    tiles.append((i, int(round(ox)), int(round(oy)), img_up))
    print(f"  [{i}] at ({ox:.0f},{oy:.0f}) size {img_up.shape[1]}x{img_up.shape[0]}")

# Warped images [0],[1]
for zi in sorted(warp_transforms):
    M_canvas, scale, inl, pi = warp_transforms[zi]
    # Adjust M for canvas origin shift and SCALE
    M_scaled = M_canvas.copy()
    M_scaled[0, 2] = (M_canvas[0, 2] - min_x) * SCALE
    M_scaled[1, 2] = (M_canvas[1, 2] - min_y) * SCALE
    M_scaled[0, 0] *= SCALE
    M_scaled[0, 1] *= SCALE
    M_scaled[1, 0] *= SCALE
    M_scaled[1, 1] *= SCALE

    # Clean the source image: paint UI chrome regions white before warping
    clean_src = images[zi].copy()
    sh, sw = clean_src.shape[:2]
    clean_src[:, :LEFT_MASK] = 255          # left toolbar
    clean_src[:5, :] = 255                  # top edge
    clean_src[sh - 30:, :] = 255            # bottom bar
    clean_src[sh - MINIMAP_H:, sw - MINIMAP_W:] = 255  # minimap

    warped = cv2.warpAffine(clean_src, M_scaled, (canvas_w, canvas_h),
                             flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_CONSTANT)

    # Coverage mask (exclude UI chrome regions)
    src_mask = np.zeros(images[zi].shape[:2], dtype=np.uint8)
    src_mask[30:sh - 50, LEFT_MASK + 20:sw - MINIMAP_W] = 255
    src_mask[30:sh - MINIMAP_H - 20, LEFT_MASK + 20:sw - 20] = 255
    warped_mask = cv2.warpAffine(src_mask, M_scaled, (canvas_w, canvas_h),
                                  flags=cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT)
    coverage = warped_mask > 128

    tiles.append((zi, warped, coverage))
    covered_pix = coverage.sum()
    print(f"  [{zi}] warped, scale={scale:.4f}, coverage={covered_pix} px")

# Build ownership map using interior distance
ownership = np.full((canvas_h, canvas_w), -1, dtype=np.int32)
best_interior = np.full((canvas_h, canvas_w), -1.0, dtype=np.float64)

# Process translation tiles
for entry in tiles:
    if len(entry) == 4:
        i, ox_i, oy_i, img_up = entry
        h, w = img_up.shape[:2]
        ey = min(oy_i + h, canvas_h)
        ex = min(ox_i + w, canvas_w)
        th, tw = ey - oy_i, ex - ox_i
        if th <= 0 or tw <= 0:
            continue

        dy = np.minimum(np.arange(0, th, dtype=np.float64),
                        np.arange(th - 1, -1, -1, dtype=np.float64))
        dx = np.minimum(np.arange(0, tw, dtype=np.float64),
                        np.arange(tw - 1, -1, -1, dtype=np.float64))
        interior = np.minimum(dy[:, None], dx[None, :])

        region_best = best_interior[oy_i:ey, ox_i:ex]
        wins = interior > region_best
        ownership[oy_i:ey, ox_i:ex][wins] = i
        region_best[wins] = interior[wins]

# Process warped tiles (for [0],[1])
for entry in tiles:
    if len(entry) == 3:
        zi, warped, coverage_raw = entry
        # Erode coverage slightly to avoid edge artifacts from warping
        kernel = np.ones((7, 7), np.uint8)
        coverage = cv2.erode(coverage_raw.astype(np.uint8), kernel, iterations=2).astype(bool)
        ys, xs = np.where(coverage)
        if len(ys) == 0:
            continue

        y0, y1 = ys.min(), ys.max() + 1
        x0, x1 = xs.min(), xs.max() + 1
        sub_coverage = coverage[y0:y1, x0:x1]

        # Compute distance transform for interior-ness
        dist = cv2.distanceTransform(sub_coverage.astype(np.uint8), cv2.DIST_L2, 5)

        region_best = best_interior[y0:y1, x0:x1]
        wins = (dist > region_best) & sub_coverage
        ownership[y0:y1, x0:x1][wins] = zi
        region_best[wins] = dist[wins]

# Paint canvas
canvas = np.full((canvas_h, canvas_w, 3), 255, dtype=np.uint8)

for entry in tiles:
    if len(entry) == 4:
        i, ox_i, oy_i, img_up = entry
        h, w = img_up.shape[:2]
        ey = min(oy_i + h, canvas_h)
        ex = min(ox_i + w, canvas_w)
        th, tw = ey - oy_i, ex - ox_i
        if th <= 0 or tw <= 0:
            continue
        mask = ownership[oy_i:ey, ox_i:ex] == i
        tile = img_up[:th, :tw]
        for c in range(3):
            canvas[oy_i:ey, ox_i:ex, c][mask] = tile[:, :, c][mask]
    elif len(entry) == 3:
        zi, warped, coverage = entry
        mask = ownership == zi
        for c in range(3):
            canvas[:, :, c][mask] = warped[:, :, c][mask]

# Inpaint white gaps
covered = ownership >= 0
if not covered.all():
    uncov = (~covered).astype(np.uint8) * 255
    canvas = cv2.inpaint(canvas, uncov, inpaintRadius=5, flags=cv2.INPAINT_TELEA)
    print(f"  Inpainted {(~covered).sum()} pixels")

out_path = "/Users/mohaned.saleh/Downloads/workflow_stitched_hires.png"
cv2.imwrite(out_path, canvas, [cv2.IMWRITE_PNG_COMPRESSION, 1])

sz = Path(out_path).stat().st_size / (1024 * 1024)
print(f"\nSaved: {out_path}")
print(f"Dimensions: {canvas_w}x{canvas_h} @ {SCALE}x")
print(f"File size: {sz:.1f} MB")
