# Fraude — asset provenance

No real customer data. All claim records are fictional.

## `case-01-a.webp`

Built-in image_gen; generated specifically for this game. Reduced to WebP, max 1200px, quality87.

Original prompt (superseded by the wider revision below):

> Use case: scientific-educational. Asset: photo for a fictional insurance fraud awareness mobile game. Create a realistic landscape 3:2 smartphone photograph of a silver compact hatchback with a dented front left fender in a European gravel parking lot. An adult in a navy jacket and jeans stands next to it, face out of frame at upper right. One hand rests flat on the upper edge of the open driver door, prominent and sharply focused in the right third. INTENTIONAL LOCALIZED SYNTHETIC ERROR: that hand visibly has six long fingers plus a thumb, all fingers clearly separated against the dark navy clothing, impossible anatomy but ordinary flesh not injury. The hand must occupy 15 percent of the image width and be easy to inspect on phone. All other scene elements credible, subdued daylight, insurance evidence candid photograph rather than ad. No text, no logos, no readable license plate, no injuries, no watermarks.

## `case-05-a.webp`

Built-in image_gen; generated specifically for this game. Reduced to WebP, max1200px, quality87.

Final prompt:

> Use case: photorealistic-natural. Asset: fictional insurance dossier photo for a mobile observation game. Landscape 3:2 candid smartphone photo, close front three-quarter view of a dark blue compact car front bumper and headlight, no license plate visible. A very distinctive pale Y-shaped scrape in the blue paint below the headlight and small dent, easily recognizable, about 20 percent of image width. Background a mottled concrete wall with a little red triangular paint stain just above the fender. Ordinary gravel parking lot, cloudy daylight, crisp detail, entirely believable European insurance evidence. No person, no words, no brand mark, no watermark. Keep both scrape and wall marker inside central 65% of image so they stay visible when cropped. Not a collage.

The observed output of case 01 contains five extended fingers and a thumb (one extra finger). The prompt asked for an even stronger anomaly; the explanation refers to the actual selected output, not the requested finger count. This is a staged educational example, not evidence of a general hand-based AI detector.

## `case-02-a.webp`

[Crashed Porsche 911 (997) front](https://commons.wikimedia.org/wiki/File:Crashed_Porsche_911_(997)_front.jpg), M 93, 2008-07-08. Source image 2259 × 1238, downloaded from Wikimedia Commons. [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/). Converted/reduced to 1200 × 658 WebP, no content edits; the distributed derivative remains CC BY-SA 3.0. Attribution and license are also visible in `/fraude/donnees`. This photograph is not linked to an actual company policyholder. The accompanying inspection report is fictional, not a factual report about the photographed accident.

## `case-05-b.svg`

The two SVG photo records now embed separate bitmap views: the original three-quarter view (`case-05-a.webp`) and a front-on view edited with built-in image_gen (`case-05-b.webp`). Their captions are drawn as native SVG: “Sinistre survenu le 12/10/2026” and “Sinistre survenu le 03/11/2026”. `tools/build-fraud-documents.py` rebuilds both records. The case teaches that repeated damage across dated claims deserves checking; it no longer claims to demonstrate an exact duplicated bitmap.

Final second-view edit prompt:

> Use case: precise-object-edit. Edit target: attached dark blue compact car front bumper photo. Create a SECOND PHOTOGRAPH of this EXACT SAME damaged car and concrete wall, taken by a person who has moved about 1 metre to the left, so the shot is closer to a FRONT-ON view instead of the original side three-quarter. Camera also a little lower, include both headlights and more front grille but crop out license plate. CRITICAL preserve exact identity and damage: same single distinctive pale Y-shaped scrape below the right-in-image headlight, same dent just right of that Y, same dark blue paint, headlight design, foglight below, mottled concrete wall with the same little red triangle paint mark. Damage must be on same physical panel, not mirrored or replaced, perspective naturally changes. Plain overcast candid smartphone insurance photo, 3:2 landscape, realistic. No new scratches, no words, no extra objects, no logos or watermarks.

## Document excerpts

Native SVGs created by `tools/build-fraud-documents.py`. Precise text, arithmetic, masked IBANs and plate mismatch are intentional. Extracts use a 900 × 640 viewBox so critical values remain readable; the game has a full-screen inspector. These are teaching documents, not real bank/garage forms. No real company logos, persons or full account identifiers.

## Fonts and characters

Press Start 2P and Pixelify Sans are copied unchanged from Recommander, with their SIL OFL notices in `mia/mia-fraude/fonts/`. The pixel avatar is adapted from the existing colleague's game with an amber palette. The robot has been replaced by a new native Canvas stack of documents, on the same 16 × 16 grid. Recommander source assets remain untouched.

## Wider accident-photo revision

Current `case-01-a.webp`: 1536 × 1024, WebP quality 94. Built-in image_gen edits widen the scene; the hand is now about 5% of the image width, with five downward fingers and a thumb verified in the selected output. Full-screen ×2/×4 zoom allows inspection on a phone. Intermediate edits that produced a normal hand were discarded.

Wide composition edit prompt:

> Use case: precise-object-edit. Edit target: attached reference photograph of the silver damaged compact car and navy-jacket person. Recompose as a wider insurance smartphone photograph taken from about 4 metres away: the WHOLE car, wheels and bumper visible, parked in the same gravel lot. The fully clothed person stands just beyond the driver door on the right, entire torso and legs, natural normal proportions. Their one bare hand rests on the top of the open door in the UPPER RIGHT area and is NORMAL SMALL anatomical scale: only about 5 to 6 percent of the total image width, not foreground. Keep the hand's localized deliberate error: five separated fingers plus one thumb (one extra finger), visible when zooming into the full-resolution photo. The main subject is the damaged car, NOT the hand. Preserve silver car with left fender dent, navy jacket and gravel lot. Neutral candid daytime phone photo, wide 3:2 landscape, realistic texture, no dramatic foreground, no text or watermark, no readable plates. No other intentional anomalies.

Final anatomy edit prompt (wide edit target plus original hand as supporting reference):

> Use case: precise-object-edit. Image 1 is the EDIT TARGET, a wide photo of a silver damaged car with fully clothed adult standing behind open door. Image 2 is a supporting REFERENCE for deliberate bad hand anatomy. Change ONLY the small hand resting on the driver's door in image 1. Reproduce the six-digit hand anatomy from image 2, at the realistic small scale of image 1: FIVE LONG FINGERS pointing DOWN over the door PLUS a separate THUMB pointing right, SIX visible fingertips total. Deliberate educational anatomical error. Draw an extra long finger between ring and middle fingers; count the downward fingers one two three four FIVE, then a thumb sideways. This should be subtly wrong, not a normal five-digit hand. The hand must remain approximately 5 percent of full photo width. Everything else unchanged, entire wide car framing unchanged. No closeup, no giant hand, no collage, no captions.
