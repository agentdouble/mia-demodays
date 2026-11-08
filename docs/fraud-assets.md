# Fraude — asset provenance

No real customer data. All claim records are fictional.

## `case-01-a.webp`

Built-in image_gen; generated specifically for this game. Reduced to WebP, max 1200px, quality87.

Final prompt:

> Use case: scientific-educational. Asset: photo for a fictional insurance fraud awareness mobile game. Create a realistic landscape 3:2 smartphone photograph of a silver compact hatchback with a dented front left fender in a European gravel parking lot. An adult in a navy jacket and jeans stands next to it, face out of frame at upper right. One hand rests flat on the upper edge of the open driver door, prominent and sharply focused in the right third. INTENTIONAL LOCALIZED SYNTHETIC ERROR: that hand visibly has six long fingers plus a thumb, all fingers clearly separated against the dark navy clothing, impossible anatomy but ordinary flesh not injury. The hand must occupy 15 percent of the image width and be easy to inspect on phone. All other scene elements credible, subdued daylight, insurance evidence candid photograph rather than ad. No text, no logos, no readable license plate, no injuries, no watermarks.

## `case-05-a.webp`

Built-in image_gen; generated specifically for this game. Reduced to WebP, max1200px, quality87.

Final prompt:

> Use case: photorealistic-natural. Asset: fictional insurance dossier photo for a mobile observation game. Landscape 3:2 candid smartphone photo, close front three-quarter view of a dark blue compact car front bumper and headlight, no license plate visible. A very distinctive pale Y-shaped scrape in the blue paint below the headlight and small dent, easily recognizable, about 20 percent of image width. Background a mottled concrete wall with a little red triangular paint stain just above the fender. Ordinary gravel parking lot, cloudy daylight, crisp detail, entirely believable European insurance evidence. No person, no words, no brand mark, no watermark. Keep both scrape and wall marker inside central 65% of image so they stay visible when cropped. Not a collage.

The observed output of case 01 contains five extended fingers and a thumb (one extra finger). The prompt asked for an even stronger anomaly; the explanation refers to the actual selected output, not the requested finger count. This is a staged educational example, not evidence of a general hand-based AI detector.

## `case-02-a.webp`

[Crashed Porsche 911 (997) front](https://commons.wikimedia.org/wiki/File:Crashed_Porsche_911_(997)_front.jpg), M 93, 2008-07-08. Source image 2259 × 1238, downloaded from Wikimedia Commons. [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/). Converted/reduced to 1200 × 658 WebP, no content edits; the distributed derivative remains CC BY-SA 3.0. Attribution and license are also visible in `/fraude/donnees`. This photograph is not linked to an actual company policyholder. The accompanying inspection report is fictional, not a factual report about the photographed accident.

## `case-05-b.svg`

A native SVG viewport of `case-05-a.webp`, crop at 112% and 10% brightness increase. The source bitmap is embedded unchanged so the distinctive Y scratch is exactly the same. This deterministic presentation transformation is intentional: it teaches reuse across two explicitly distinct vehicles. No fresh AI generation is substituted for the reused photo.

## Document excerpts

Native SVGs created by `tools/build-fraud-documents.py`. Precise text, arithmetic, masked IBANs and plate mismatch are intentional. Extracts use a 900 × 640 viewBox so critical values remain readable; the game has a full-screen inspector. These are teaching documents, not real bank/garage forms. No real company logos, persons or full account identifiers.

## Fonts and characters

Press Start 2P and Pixelify Sans are copied unchanged from Recommander, with their SIL OFL notices in `mia/mia-fraude/fonts/`. Pixel avatar and robot drawings are adapted from the existing colleague's game with an amber palette. Recommander source assets remain untouched.
