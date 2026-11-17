/**
 * ModScreenshotGallery - a mod's screenshots on its detail page (Story 18.1, VSS-l4x).
 *
 * One image at a time with its position ("3 of 10"), Previous and Next, and a strip of
 * the mod database's 55x60 thumbnails. Activating the image opens it larger in a
 * dialog that shares the position with the section. Previous and Next wrap around.
 *
 * Epic 18 ADR-2:
 * - Only the current image's full-size file is requested; the strip uses thumbnails.
 *   Every `<img>` has `loading="lazy"` (before `src`) and `referrerPolicy="no-referrer"`.
 * - Left and Right arrow keys move one image while focus is in the section or in the
 *   dialog. The two handlers are siblings in the React tree: React events bubble
 *   through portals, so a dialog inside the section would step twice per key press.
 *   Nothing listens on `document`.
 * - Previous, Next and every thumbnail are at least 44x44px.
 *
 * The URLs were checked by the API (`services/mod_media.py`); they are not checked again.
 */

import { useEffect, useRef, useState, type KeyboardEvent } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { cn } from '@/lib/utils';
import type { ModScreenshot } from '@/api/types';

interface ModScreenshotGalleryProps {
  screenshots: ModScreenshot[];
}

/** "Screenshot 3 of 10: ToolRepair.png", or "Screenshot 3 of 10" without a file name. */
function screenshotAlt(index: number, count: number, filename: string): string {
  const base = `Screenshot ${index + 1} of ${count}`;
  return filename ? `${base}: ${filename}` : base;
}

export function ModScreenshotGallery({ screenshots }: ModScreenshotGalleryProps) {
  const [index, setIndex] = useState(0);
  const [open, setOpen] = useState(false);
  const thumbRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const scrolledIndex = useRef(0);

  const count = screenshots.length;
  // Clamp in case the list got shorter
  const current = Math.min(index, Math.max(count - 1, 0));
  const several = count > 1;

  // Keep the selected thumbnail visible in the strip; not on first render (it would
  // scroll the page) and not while the dialog covers the strip
  useEffect(() => {
    if (open || current === scrolledIndex.current) return;
    scrolledIndex.current = current;
    thumbRefs.current[current]?.scrollIntoView({ block: 'nearest', inline: 'nearest' });
  }, [current, open]);

  if (count === 0) return null;

  const step = (delta: number) => setIndex((current + delta + count) % count);

  const handleArrows = (event: KeyboardEvent) => {
    if (!several || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
    if (event.key === 'ArrowLeft') {
      event.preventDefault();
      step(-1);
    } else if (event.key === 'ArrowRight') {
      event.preventDefault();
      step(1);
    }
  };

  const shot = screenshots[current];
  const alt = screenshotAlt(current, count, shot.filename);
  const positionText = `${current + 1} of ${count}`;

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <Card data-testid="mod-screenshots" onKeyDown={handleArrows}>
        <CardHeader>
          <CardTitle className="text-lg">Screenshots</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <DialogTrigger asChild>
            <button
              type="button"
              className="block w-full aspect-video overflow-hidden rounded-md bg-muted outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
              data-testid="mod-screenshot-current"
            >
              <img
                loading="lazy"
                src={shot.imageUrl}
                alt={alt}
                referrerPolicy="no-referrer"
                className="h-full w-full object-contain"
                data-testid="mod-screenshot-image"
              />
              <span className="sr-only">View larger</span>
            </button>
          </DialogTrigger>

          {several && (
            <>
              <div className="flex items-center justify-center gap-4">
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  className="size-11"
                  aria-label="Previous screenshot"
                  onClick={() => step(-1)}
                  data-testid="mod-screenshot-prev"
                >
                  <ChevronLeft aria-hidden="true" />
                </Button>
                <span
                  aria-live="polite"
                  className="min-w-16 text-center text-sm text-muted-foreground"
                  data-testid="mod-screenshot-position"
                >
                  {positionText}
                </span>
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  className="size-11"
                  aria-label="Next screenshot"
                  onClick={() => step(1)}
                  data-testid="mod-screenshot-next"
                >
                  <ChevronRight aria-hidden="true" />
                </Button>
              </div>

              <div
                className="flex gap-2 overflow-x-auto p-1"
                data-testid="mod-screenshot-thumbnails"
              >
                {screenshots.map((thumb, i) => (
                  <button
                    key={`${i}-${thumb.imageUrl}`}
                    type="button"
                    ref={(element) => {
                      thumbRefs.current[i] = element;
                    }}
                    aria-current={i === current ? 'true' : undefined}
                    onClick={() => setIndex(i)}
                    className={cn(
                      'shrink-0 overflow-hidden rounded-md border bg-muted outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50',
                      i === current && 'ring-2 ring-primary'
                    )}
                    data-testid={`mod-screenshot-thumb-${i}`}
                  >
                    <img
                      loading="lazy"
                      src={thumb.thumbnailUrl}
                      alt={screenshotAlt(i, count, thumb.filename)}
                      referrerPolicy="no-referrer"
                      width={55}
                      height={60}
                      className="block h-[60px] w-[55px] object-cover"
                    />
                  </button>
                ))}
              </div>
            </>
          )}
        </CardContent>
      </Card>

      <DialogContent
        className="p-3 sm:max-w-5xl sm:p-4"
        onKeyDown={handleArrows}
        data-testid="mod-screenshot-dialog"
      >
        <DialogTitle className="sr-only">{alt}</DialogTitle>
        <DialogDescription className="sr-only">
          Use the left and right arrow keys to move between screenshots.
        </DialogDescription>
        <img
          loading="lazy"
          src={shot.imageUrl}
          alt={alt}
          referrerPolicy="no-referrer"
          className="max-h-[80vh] w-full object-contain"
          data-testid="mod-screenshot-dialog-image"
        />
        {several && (
          <div className="flex items-center justify-center gap-4">
            <Button
              type="button"
              variant="outline"
              size="icon"
              className="size-11"
              aria-label="Previous screenshot"
              onClick={() => step(-1)}
              data-testid="mod-screenshot-dialog-prev"
            >
              <ChevronLeft aria-hidden="true" />
            </Button>
            <span
              aria-live="polite"
              className="min-w-16 text-center text-sm text-muted-foreground"
              data-testid="mod-screenshot-dialog-position"
            >
              {positionText}
            </span>
            <Button
              type="button"
              variant="outline"
              size="icon"
              className="size-11"
              aria-label="Next screenshot"
              onClick={() => step(1)}
              data-testid="mod-screenshot-dialog-next"
            >
              <ChevronRight aria-hidden="true" />
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
