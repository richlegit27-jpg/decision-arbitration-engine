import re


class AttachmentKeypointsService:

    def attachment_keypoints_from_text(
        self,
        text,
        max_points=10,
    ):
        points = []

        for line in str(text or "").splitlines():
            cleaned = re.sub(
                r"\s+",
                " ",
                line,
            ).strip()

            if not cleaned:
                continue

            if len(cleaned) < 20:
                continue

            points.append(cleaned)

            if len(points) >= max_points:
                break

        return points