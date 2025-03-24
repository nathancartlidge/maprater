from pathlib import Path

import cv2
import numpy as np
import matplotlib.pyplot as plt

# manually calculated with some trial and error
COLS = [0.38, 0.45, 0.52, 0.595, 0.74, 0.865, 0.985]
COL_KEYS = ["K", "A", "D", "Damage", "Healing", "Mitigated"]
ROWS = [0.02, 0.2, 0.4, 0.6, 0.8, 0.98]


def detect_team_boxes(image_path):
    """
    Detects bounding boxes for blue and red team sections in the scoreboard image.

    Args:
        image_path (str): Path to the scoreboard image.

    Returns:
        dict: Dictionary containing bounding boxes for 'blue' and 'red' teams, or None if detection fails.
    """
    img = cv2.imread(image_path)
    if img is None:
        print(f"Error: Could not read image at {image_path}")
        return None

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # --- Define HSV color ranges for blue and red ---
    # Adjust these ranges if needed based on your images
    lower_blue = np.array([90, 240, 120])   # Example blue range
    upper_blue = np.array([100, 255, 190])
    lower_red = np.array([160, 200, 110])    # Example red range (adjust hue for reds if needed, may need to split range)
    upper_red = np.array([180, 220, 140])

    kernel = np.ones((5, 5), np.uint8)

    blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)
    blue_mask_dilated = cv2.dilate(blue_mask, kernel, iterations=2)

    red_mask = cv2.inRange(hsv, lower_red, upper_red)
    red_mask_dilated = cv2.dilate(red_mask, kernel, iterations=2)

    team_bboxes = {}

    for color, mask in zip(["blue", "red"], [blue_mask_dilated, red_mask_dilated]):
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if contours:
            # Find the largest contour - assuming it's the team box
            largest_contour = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(largest_contour)
            team_bboxes[color] = (x, y, x + w, y + h) # Store as (x_start, y_start, x_end, y_end)
        else:
            print(f"Warning: No contours detected for {color} team.")
            return None # Or handle no detection differently

    if 'blue' in team_bboxes and 'red' in team_bboxes:
        return team_bboxes
    else:
        print("Error: Could not detect both blue and red team boxes.")
        return None


def split_teams(image_path):
    image = cv2.imread(image_path)

    team_boxes = detect_team_boxes(image_path)
    blue_box = team_boxes['blue']
    red_box = team_boxes['red']

    blue_team = image[blue_box[1]:blue_box[3], blue_box[0]:blue_box[2]]
    red_team = image[red_box[1]:red_box[3], red_box[0]:red_box[2]]

    blue_scale_factor = 1000 / blue_team.shape[1]
    red_scale_factor = 1000 / blue_team.shape[1]

    if blue_team.shape[1] < 400 or red_team.shape[1] < 400:
        raise ValueError("bad size detected!")

    blue_team = cv2.resize(blue_team,
                           (int(blue_team.shape[1] * blue_scale_factor), int(blue_team.shape[0] * blue_scale_factor)),
                           interpolation=cv2.INTER_LANCZOS4)
    red_team = cv2.resize(red_team,
                          (int(red_team.shape[1] * red_scale_factor), int(red_team.shape[0] * red_scale_factor)),
                          interpolation=cv2.INTER_LANCZOS4)

    return blue_team, red_team


def split_digits(image, verbose: bool = False):
    # Find contours for individual characters (digits, commas)
    kernel = np.ones((5, 5), np.uint8)
    # image_dilated = cv2.dilate(image, kernel, iterations=1)
    contours, _ = cv2.findContours(image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Sort contours left-to-right
    contours = sorted(contours, key=lambda c: cv2.boundingRect(c)[0])

    # Process each contour
    result = []

    if verbose:
        print("found", len(contours), "contours")

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        char_image = image[y:y+h, x:x+w]

        # Determine if digit or comma by aspect ratio and area
        if h < 10:  # Likely a comma
            continue
        elif w >= 20 or h >= 20:
            print(f"error: image ({w}, {h}) is too large! skipping")
            continue

        # likely a digit - add it!
        # place on a consistent background
        bg = np.zeros(shape=(20, 20), dtype=np.uint8)
        margin_h, margin_w = 20 - char_image.shape[0], 20 - char_image.shape[1]
        bg[margin_h // 2:char_image.shape[0] + margin_h // 2, margin_w // 2:char_image.shape[1] + margin_w // 2] += char_image.astype(np.uint8)
        result.append(bg)

    return result


def recognize_digit_with_templates(digit_image, templates, threshold=0.7, plot: bool = False,
                                   show_scores: bool = False):
    """
    Recognize a single digit using template matching.

    Args:
        digit_image: Image containing a single digit
        threshold: Minimum score to consider a match valid

    Returns:
        Recognized digit (0-9) or -1 if no confident match
    """
    best_score = -1
    best_digit = -1

    # Try each template
    for digit, digit_templates in templates.items():
        for template in digit_templates:
            if np.sum(template) == 0:
                continue

            # Resize template to match digit image if needed
            if template.shape != digit_image.shape:
                template = cv2.resize(template, (digit_image.shape[1], digit_image.shape[0]))

            # Match the template
            result = cv2.matchTemplate(digit_image, template, cv2.TM_CCORR_NORMED)
            score = np.max(result)

            if plot:
                plt.imshow(digit_image)
                plt.show()
                plt.imshow(template)
                plt.show()

            if show_scores:
               print(digit, score)

            if score > best_score:
                best_score = score
                best_digit = digit

    # Return the digit if score is above threshold
    if best_score >= threshold:
        return str(best_digit), best_score
    else:
        return "x", best_score

def load_templates(path: Path | str):
    arr = np.load(path)
    return {k: v for k, v in enumerate(arr)}


def read_scoreboard(team_image, templates):
    data = []
    for r1, r2 in zip(ROWS, ROWS[1:]):
        player = {}
        for key, c1, c2 in zip(COL_KEYS, COLS, COLS[1:]):
            x1, x2 = int(c1 * team_image.shape[1]), int(c2 * team_image.shape[1])
            y1, y2 = int(r1 * team_image.shape[0]), int(r2 * team_image.shape[0])

            box = team_image[y1:y2, x1:x2]
            gray = cv2.cvtColor(box, cv2.COLOR_BGR2GRAY)

            # todo: prevent it from going insane on edges
            thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_OTSU)[1]
            player[key] = "".join([recognize_digit_with_templates(d, templates=templates)[0] for d in split_digits(thresh)])
        data.append(player)
    return data


def print_scoreboards(blue_team, red_team):
    for key in COL_KEYS:
        print(f"{''.join(key): >10}", end=" ")
    print()

    for team in [blue_team, red_team]:
        for player in team:
            for value in player.values():
                print(f"{''.join(value): >10}", end=" ")
            print()
        print()
