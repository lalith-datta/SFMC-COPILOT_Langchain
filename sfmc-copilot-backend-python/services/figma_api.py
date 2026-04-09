"""
Figma REST API Client Service.

Fetches design data from Figma files and exports images for use
in the Figma → SFMC email creation pipeline.
"""

import json
import logging
import re
from typing import Any

import httpx

from config import settings

logger = logging.getLogger(__name__)

FIGMA_API_BASE = "https://api.figma.com/v1"


class FigmaApiService:
    def __init__(self) -> None:
        self._client = httpx.Client(timeout=60.0)

    # -------------------- helpers --------------------

    def _headers(self) -> dict[str, str]:
        if not settings.figma_access_token:
            raise RuntimeError(
                "FIGMA_ACCESS_TOKEN not configured. "
                "Set it in your .env file."
            )
        return {"X-Figma-Token": settings.figma_access_token}

    # -------------------- URL parsing --------------------

    @staticmethod
    def parse_figma_url(url: str) -> dict[str, str | None]:
        """Extract file_key and optional node_id from a Figma URL.

        Supported formats:
        - https://www.figma.com/file/ABC123/FileName
        - https://www.figma.com/design/ABC123/FileName
        - https://www.figma.com/file/ABC123/FileName?node-id=1:2
        - https://www.figma.com/design/ABC123/FileName?node-id=1-2
        """
        # Match file or design URL patterns
        match = re.search(r"figma\.com/(?:file|design)/([a-zA-Z0-9]+)", url)
        if not match:
            raise ValueError(f"Invalid Figma URL: {url}")

        file_key = match.group(1)

        # Extract node-id if present (can be 1:2 or 1-2 format)
        node_match = re.search(r"node-id=([^&]+)", url)
        node_id = None
        if node_match:
            # Figma URLs use - instead of : for node IDs, convert back
            node_id = node_match.group(1).replace("-", ":")

        return {"file_key": file_key, "node_id": node_id}

    # -------------------- API calls --------------------

    def get_file(self, file_key: str) -> dict:
        """Fetch the full Figma file document tree."""
        url = f"{FIGMA_API_BASE}/files/{file_key}"
        logger.info("Fetching Figma file: %s", file_key)
        resp = self._client.get(url, headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    def get_file_nodes(self, file_key: str, node_ids: list[str]) -> dict:
        """Fetch specific nodes from a Figma file."""
        url = f"{FIGMA_API_BASE}/files/{file_key}/nodes"
        ids_param = ",".join(node_ids)
        logger.info("Fetching Figma nodes: %s from file %s", ids_param, file_key)
        resp = self._client.get(
            url, headers=self._headers(), params={"ids": ids_param}
        )
        resp.raise_for_status()
        return resp.json()

    def get_images(
        self, file_key: str, node_ids: list[str], fmt: str = "png", scale: int = 2
    ) -> dict[str, str]:
        """Export Figma nodes as images and return {node_id: image_url} map."""
        url = f"{FIGMA_API_BASE}/images/{file_key}"
        ids_param = ",".join(node_ids)
        logger.info("Exporting images for nodes: %s (format=%s)", ids_param, fmt)
        resp = self._client.get(
            url,
            headers=self._headers(),
            params={"ids": ids_param, "format": fmt, "scale": scale},
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("images", {})

    # -------------------- Design extraction --------------------

    def extract_email_structure(self, file_data: dict, node_id: str | None = None) -> dict:
        """Extract a simplified email structure from Figma file data.

        Walks the node tree and extracts: text content, colors, fonts,
        images, layout information. Returns a structured dict suitable
        for passing to Gemini for HTML generation.
        """
        document = file_data.get("document", {})

        # If a specific node_id is given, find that node; otherwise use first page's first frame
        if node_id:
            target_node = self._find_node_by_id(document, node_id)
            if not target_node:
                raise ValueError(f"Node {node_id} not found in Figma file.")
        else:
            # Use the first frame on the first page
            pages = document.get("children", [])
            if not pages:
                raise ValueError("Figma file has no pages.")
            first_page = pages[0]
            frames = [c for c in first_page.get("children", []) if c.get("type") == "FRAME"]
            if not frames:
                raise ValueError("No frames found on the first page.")
            target_node = frames[0]

        # Extract the design structure recursively
        structure = self._extract_node(target_node)
        structure["_metadata"] = {
            "file_name": file_data.get("name", ""),
            "root_frame_name": target_node.get("name", ""),
            "root_frame_size": {
                "width": target_node.get("absoluteBoundingBox", {}).get("width"),
                "height": target_node.get("absoluteBoundingBox", {}).get("height"),
            },
        }
        return structure

    def _find_node_by_id(self, node: dict, target_id: str) -> dict | None:
        """Recursively search for a node by its ID."""
        if node.get("id") == target_id:
            return node
        for child in node.get("children", []):
            found = self._find_node_by_id(child, target_id)
            if found:
                return found
        return None

    def _extract_node(self, node: dict) -> dict:
        """Recursively extract relevant design properties from a node."""
        node_type = node.get("type", "UNKNOWN")
        extracted: dict[str, Any] = {
            "type": node_type,
            "name": node.get("name", ""),
        }

        # Dimensions
        bbox = node.get("absoluteBoundingBox")
        if bbox:
            extracted["bounds"] = {
                "x": bbox.get("x"),
                "y": bbox.get("y"),
                "width": bbox.get("width"),
                "height": bbox.get("height"),
            }

        # Background / fill colors
        fills = node.get("fills", [])
        if fills:
            extracted["fills"] = []
            for fill in fills:
                if fill.get("visible", True) is False:
                    continue
                fill_info: dict[str, Any] = {"type": fill.get("type", "SOLID")}
                color = fill.get("color")
                if color:
                    fill_info["color"] = {
                        "r": round(color.get("r", 0) * 255),
                        "g": round(color.get("g", 0) * 255),
                        "b": round(color.get("b", 0) * 255),
                        "a": round(color.get("a", 1), 2),
                    }
                if fill.get("type") == "IMAGE":
                    fill_info["imageRef"] = fill.get("imageRef")
                extracted["fills"].append(fill_info)

        # Text content
        if node_type == "TEXT":
            extracted["text"] = node.get("characters", "")
            style = node.get("style", {})
            extracted["textStyle"] = {
                "fontFamily": style.get("fontFamily", "Arial"),
                "fontSize": style.get("fontSize", 14),
                "fontWeight": style.get("fontWeight", 400),
                "textAlignHorizontal": style.get("textAlignHorizontal", "LEFT"),
                "lineHeightPx": style.get("lineHeightPx"),
                "letterSpacing": style.get("letterSpacing", 0),
            }
            # Text fill color
            text_fills = node.get("fills", [])
            if text_fills:
                for tf in text_fills:
                    tc = tf.get("color")
                    if tc:
                        extracted["textStyle"]["color"] = {
                            "r": round(tc.get("r", 0) * 255),
                            "g": round(tc.get("g", 0) * 255),
                            "b": round(tc.get("b", 0) * 255),
                        }
                        break

        # Padding & layout
        if "paddingLeft" in node:
            extracted["padding"] = {
                "top": node.get("paddingTop", 0),
                "right": node.get("paddingRight", 0),
                "bottom": node.get("paddingBottom", 0),
                "left": node.get("paddingLeft", 0),
            }

        if "layoutMode" in node:
            extracted["layout"] = {
                "mode": node.get("layoutMode"),  # HORIZONTAL or VERTICAL
                "itemSpacing": node.get("itemSpacing", 0),
                "primaryAxisAlignItems": node.get("primaryAxisAlignItems"),
                "counterAxisAlignItems": node.get("counterAxisAlignItems"),
            }

        # Corner radius
        corner_radius = node.get("cornerRadius")
        if corner_radius:
            extracted["cornerRadius"] = corner_radius

        # Strokes / borders
        strokes = node.get("strokes", [])
        if strokes:
            for stroke in strokes:
                if stroke.get("visible", True) is False:
                    continue
                sc = stroke.get("color")
                if sc:
                    extracted["border"] = {
                        "color": {
                            "r": round(sc.get("r", 0) * 255),
                            "g": round(sc.get("g", 0) * 255),
                            "b": round(sc.get("b", 0) * 255),
                        },
                        "weight": node.get("strokeWeight", 1),
                    }
                    break

        # Recurse into children
        children = node.get("children", [])
        if children:
            extracted["children"] = []
            for child in children:
                if child.get("visible", True) is False:
                    continue
                extracted["children"].append(self._extract_node(child))

        return extracted

    # -------------------- High-level pipeline --------------------

    def fetch_design_for_email(self, figma_url: str) -> dict:
        """Complete pipeline: parse URL → fetch file → extract structure → collect image nodes.

        Returns a dict with:
            - 'structure': the simplified design tree
            - 'image_nodes': list of node IDs that contain images
            - 'file_key': the Figma file key
        """
        parsed = self.parse_figma_url(figma_url)
        file_key = parsed["file_key"]
        node_id = parsed["node_id"]

        if node_id:
            # Fetch just the specific node
            nodes_data = self.get_file_nodes(file_key, [node_id])
            nodes = nodes_data.get("nodes", {})
            node_data = nodes.get(node_id, {})
            # Build a minimal file-like structure
            file_data = {
                "name": nodes_data.get("name", ""),
                "document": node_data.get("document", node_data),
            }
            structure = self._extract_node(
                node_data.get("document", node_data)
            )
            structure["_metadata"] = {
                "file_name": file_data.get("name", ""),
                "root_frame_name": structure.get("name", ""),
                "root_frame_size": structure.get("bounds", {}),
            }
        else:
            file_data = self.get_file(file_key)
            structure = self.extract_email_structure(file_data, node_id)

        # Collect image node IDs for export
        image_nodes = self._collect_image_nodes(structure)

        return {
            "structure": structure,
            "image_node_ids": image_nodes,
            "file_key": file_key,
        }

    def _collect_image_nodes(self, node: dict) -> list[str]:
        """Find all nodes that have IMAGE fills (need to be exported)."""
        image_ids = []
        fills = node.get("fills", [])
        for fill in fills:
            if fill.get("type") == "IMAGE":
                # Use node name as identifier since we don't store the id in extracted
                image_ids.append(fill.get("imageRef", ""))
        for child in node.get("children", []):
            image_ids.extend(self._collect_image_nodes(child))
        return image_ids


# Singleton instance
figma_api_service = FigmaApiService()
