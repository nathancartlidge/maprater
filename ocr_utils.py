import logging
from pathlib import Path

import cv2
import requests
import numpy as np
import matplotlib.pyplot as plt

import discord
from discord import ApplicationContext
from discord.commands import Option, slash_command
from discord.ext import commands

# manually calculated with some trial and error
COLS = [0.38, 0.45, 0.52, 0.595, 0.74, 0.865, 0.985]
COL_KEYS = ["K", "A", "D", "Damage", "Heal.", "Mit."]
ROWS = [0.02, 0.2, 0.4, 0.6, 0.8, 0.98]


def detect_team_boxes(image: Path | str | np.ndarray):
    """
    Detects bounding boxes for blue and red team sections in the scoreboard image.

    Args:
        image_path (str): Path to the scoreboard image.

    Returns:
        dict: Dictionary containing bounding boxes for 'blue' and 'red' teams, or None if detection fails.
    """
    if isinstance(image, (str, Path)):
        img = cv2.imread(image)
        if img is None:
            print(f"Error: Could not read image at {image}")
            return None
    else:
        img = image

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # --- Define HSV color ranges for blue and red ---
    # Adjust these ranges if needed based on your images
    lower_blue = np.array([90, 235, 120])   # Example blue range
    upper_blue = np.array([105, 255, 195])
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


def split_teams(image_path: Path | str | np.ndarray):
    if isinstance(image_path, (str, Path)):
        image = cv2.imread(image_path)
        if image is None:
            print(f"Error: Could not read image at {image_path}")
            return None
    else:
        image = image_path

    team_boxes = detect_team_boxes(image)
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
        score = 0
        count = 0
        for template in digit_templates:
            if np.sum(template) == 0:
                continue

            # Resize template to match digit image if needed
            if template.shape != digit_image.shape:
                template = cv2.resize(template, (digit_image.shape[1], digit_image.shape[0]))

            # Match the template
            result = cv2.matchTemplate(digit_image, template, cv2.TM_CCORR_NORMED)
            score += np.max(result)
            count += 1

            if plot:
                plt.imshow(digit_image)
                plt.show()
                plt.imshow(template)
                plt.show()

        # get average not maximum score
        score /= count

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


class OcrCog(commands.Cog):
    def __init__(self, base):
        self.templates = load_templates(base / "templates.npy")

    @staticmethod
    def download_file(url):
        logging.info("downloading image from %s", url)

        req = requests.get(url)
        if req.status_code != 200:
            return None

        buf = np.asarray(bytearray(req.content), dtype=np.uint8)
        img = cv2.imdecode(buf, -1)  # 'Load it as it is'
        return img

    @staticmethod
    def scoreboards(blue_scoreboard, red_scoreboard):
        data = ""
        for key in COL_KEYS:
            if key in ["K", "A", "D"]:
                data += f"{key: >3}"
            else:
                data += f" {key: >6}"

        data += "\n"

        for scoreboard in [blue_scoreboard, red_scoreboard]:
            for player in scoreboard:
                for key, value in player.items():
                    if key in ["K", "A", "D"]:
                        data += f"{value: >3}"
                    else:
                        data += f" {value: >6}"
                data += "\n"
            data += "\n"

        return data

    @staticmethod
    def stats(blue_scoreboard, red_scoreboard):
        try:
            stats = ""
            for team_name, scoreboard, enemy_scoreboard in zip(["blue", "red"], [blue_scoreboard, red_scoreboard],
                                                               [red_scoreboard, blue_scoreboard]):
                d = sum(int(player["D"]) for player in scoreboard)
                dmg = sum(int(player["Damage"]) for player in scoreboard) / 1000
                heal = sum(int(player["Heal."]) for player in scoreboard) / 1000
                mit = sum(int(player["Mit."]) for player in scoreboard) / 1000

                enemy_d = sum(int(player["D"]) for player in enemy_scoreboard)
                enemy_dmg = sum(int(player["Damage"]) for player in enemy_scoreboard) / 1000
                enemy_heal = sum(int(player["Heal."]) for player in enemy_scoreboard) / 1000

                stats += f"**{team_name.title()} Team:** {enemy_d}-{d}\n" \
                     f"\t{dmg:.1f}k damage dealt ({dmg / enemy_d:.1f}k per elim)\n" \
                     f"\t{dmg - enemy_heal:.1f}k net damage dealt ({(dmg - enemy_heal) / enemy_d:.1f}k per elim)\n" \
                     f"\t{heal:.1f}k healed ({100 * heal / enemy_dmg:.0f}% of enemy damage)\n" \
                     f"\t{mit:.1f}k mitigated ({100 * mit / (enemy_dmg + mit):.0f}% of hits landed)\n\n"
            return stats
        except ValueError:
            return None

    @slash_command(description="use OCR to detect team stats")
    async def scoreboard(self, ctx: ApplicationContext,
                         file: Option(discord.Attachment, description="The scoreboard to OCR", required=True),
                         show_scoreboard: Option(bool, description="show the parsed scoreboard", required=False, default=False)):
        """Read a scoreboard using OCR, show some basic stats"""
        logging.info("OCR - Invoked by %s", ctx.author)
        if ctx.guild_id is None:
            await ctx.respond(":warning: This bot does not support DMs")
            return

        assert isinstance(file, discord.Attachment)

        if "image" not in file.content_type:
            await ctx.respond(
                content=":warning: Bad attachment type",
                ephemeral=True
            )
            raise ValueError("Bad attachment")

        await ctx.defer(ephemeral=True)

        img = self.download_file(file.url)
        if img is None:
            await ctx.respond(
                content=":warning: Unable to download attachment",
                ephemeral=True
            )
            raise IOError("Unable to download attachment")

        logging.info("parsing the image...")

        try:
            blue_team, red_team = split_teams(img)
            blue_scoreboard = read_scoreboard(blue_team, self.templates)
            red_scoreboard = read_scoreboard(red_team, self.templates)
        except:
            await ctx.respond(
                content=":warning: Unable to parse image",
                ephemeral=True
            )
            return

        logging.info("calculating stats...")

        data = self.scoreboards(blue_scoreboard, red_scoreboard)
        stats = self.stats(blue_scoreboard, red_scoreboard)

        if stats is not None:
            disclaimer = "-# these numbers have been made up by a computer and as such could be wrong! " \
                         "(also stats are kinda meaningless so don't over-index on them)"
            if show_scoreboard:
                await ctx.respond(
                    content=stats[:-2] + f"\n\n```{data}```\n{disclaimer}",
                    ephemeral=True
                )
            else:
                await ctx.respond(
                    content=stats[:-2] + "\n\n" + disclaimer,
                    ephemeral=True
                )
        else:
            await ctx.respond(
                content=f":warning: Failed to compute stats from data: unfortunately, this bot does not yet support "
                        f"in-match screenshots or weird colours\n\nBest attempt:```\n{data}```",
                ephemeral=True
            )
