# Images

DocsForge handles images with enhanced styling options. Images are responsive by default and support lazy loading, alignment, sizing, and more.

---

## Basic image

Standard Markdown syntax:

``` markdown
![Alt text](assets/images/screenshot.png)
```

![Alt text](assets/images/screenshot.png)

Always use descriptive alt text for accessibility and SEO.

---

## Image with caption

Use `figure` markup for captions:

``` markdown
<figure markdown="span">
  ![Screenshot](assets/images/screenshot.png)
  <figcaption>Documentation site preview</figcaption>
</figure>
```

<figure markdown="span">
  ![Screenshot](assets/images/screenshot.png)
  <figcaption>Documentation site preview</figcaption>
</figure>

---

## Image alignment

### Left aligned

``` markdown
![Image](assets/images/screenshot.png){ align=left }
```

Text wraps around the image on the right.

### Right aligned

``` markdown
![Image](assets/images/screenshot.png){ align=right }
```

Text wraps around the image on the left.

### Center aligned

``` markdown
![Image](assets/images/screenshot.png){ align=center }
```

Image is centered with text above and below.

---

## Image size

Set width and height:

``` markdown
![Image](assets/images/screenshot.png){ width="300" }
```

Set width as a percentage:

``` markdown
![Image](assets/images/screenshot.png){ width="50%" }
```

Set both width and height:

``` markdown
![Image](assets/images/screenshot.png){ width="300" height="200" }
```

!!! warning "Aspect ratio"
    Setting both width and height may distort the image. Use `width` alone to maintain aspect ratio.

---

## Lazy loading

Images load lazily by default. To disable for above-the-fold images (like hero banners):

``` markdown
![Hero image](assets/images/hero.png){ loading=eager }
```

| Value | Behavior |
|-------|----------|
| `lazy` (default) | Load when image enters viewport |
| `eager` | Load immediately with page |

---

## Shadow effect

Add a subtle shadow for depth:

``` markdown
![Image](assets/images/screenshot.png){ .shadow }
```

This works well for screenshots and UI mockups to separate them from the page background.

---

## Linking images

Make an image a link:

``` markdown
[![Alt text](assets/images/screenshot.png)](https://example.com)
```

Open in new tab:

``` markdown
[![Alt text](assets/images/screenshot.png)](https://example.com){ target="_blank" }
```

---

## Lightbox (click to enlarge)

DocsForge supports lightbox mode for images. Click any image to see it full size:

``` markdown
![Diagram](assets/images/diagram.png){ data-lightbox }
```

This is enabled automatically for most images. No configuration needed.

---

## Image gallery

Create a grid of images:

``` markdown
<div class="grid" markdown>

![Image 1](assets/images/1.png)
![Image 2](assets/images/2.png)
![Image 3](assets/images/3.png)

</div>
```

---

## Responsive images

DocsForge automatically makes images responsive. They:
- Scale to fit their container
- Never overflow the content area
- Maintain aspect ratio
- Work on all screen sizes

No configuration needed.

---

## Image formats

Recommended formats:

| Format | Best for | Size |
|--------|----------|------|
| SVG | Logos, icons, diagrams | Smallest, infinite scale |
| WebP | Screenshots, photos | ~25% smaller than PNG/JPEG |
| PNG | Screenshots with transparency | Lossless, larger |
| JPEG | Photos without transparency | Good compression |

### Convert to WebP

``` bash
# Using cwebp
cwebp -q 85 image.png -o image.webp

# Using ImageMagick
convert image.png -quality 85 image.webp
```

---

## Optimization tips

1. **Use WebP when possible** — smaller than PNG/JPEG with similar quality
2. **Compress images** before adding to docs (use tinypng.com, ImageMagick, or ffmpeg)
3. **Use SVG** for logos, icons, and simple diagrams
4. **Keep under 200KB** when possible — larger images slow page load
5. **Use descriptive alt text** — important for accessibility and SEO
6. **Lazy load by default** — only use `eager` for above-the-fold images
7. **Consider dark mode** — use transparent PNGs or SVGs for dark theme compatibility

### Image sizing guidelines

| Type | Recommended size | Format |
|------|-----------------|--------|
| Logo | 200×50px | SVG |
| Screenshot | 800-1200px wide | WebP/PNG |
| Diagram | Vector | SVG |
| Icon | 24×24px | SVG |
| Hero banner | 1200×400px | WebP/JPEG |

---

## Next steps

- [Icons & Emojis](icons-emojis.md)
- [Lists](lists.md)
- [Data tables](data-tables.md)
