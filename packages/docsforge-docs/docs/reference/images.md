# Images

DocsForge handles images with enhanced styling options.

## Basic image

Standard Markdown syntax:

``` markdown
![Alt text](assets/images/screenshot.png)
```

## Image with caption

Use `figure` markup for captions:

``` markdown
<figure markdown="span">
  ![Screenshot](assets/images/screenshot.png)
  <figcaption>Documentation site preview</figcaption>
</figure>
```

## Image alignment

### Left aligned

``` markdown
![Image](assets/images/screenshot.png){ align=left }
```

### Right aligned

``` markdown
![Image](assets/images/screenshot.png){ align=right }
```

### Center aligned

``` markdown
![Image](assets/images/screenshot.png){ align=center }
```

## Image size

Set width and height:

``` markdown
![Image](assets/images/screenshot.png){ width="300" }
```

``` markdown
![Image](assets/images/screenshot.png){ width="50%" }
```

## Lazy loading

Images load lazily by default. To disable for above-the-fold images:

``` markdown
![Hero image](assets/images/hero.png){ loading=eager }
```

## Shadow

Add a shadow effect:

``` markdown
![Image](assets/images/screenshot.png){ .shadow }
```

## Linking images

Make an image a link:

``` markdown
[![Alt text](assets/images/screenshot.png)](https://example.com)
```

## Responsive images

DocsForge automatically makes images responsive. They scale to fit their container and don't overflow.

## Image formats

Recommended formats:

| Format | Use case |
|--------|----------|
| PNG | Screenshots, diagrams with transparency |
| JPEG | Photos, complex images |
| WebP | All of the above (smaller file size) |
| SVG | Icons, logos, simple diagrams |

## Optimization tips

1. Use WebP when possible (smaller than PNG/JPEG)
2. Compress images before adding to docs
3. Use SVG for logos and icons
4. Keep images under 200KB when possible
5. Use descriptive alt text for accessibility

## Next steps

- [Icons & Emojis](icons-emojis.md)
- [Lists](lists.md)
