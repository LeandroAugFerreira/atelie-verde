export type SearchImage = {
  image_url: string;
  thumbnail_url?: string;
  source_url: string;
  domain?: string;
  caption?: string;
};

export function publicWebUrl(value: string) {
  try {
    const url = new URL(value);
    const host = url.hostname;
    return ["https:", "http:"].includes(url.protocol) &&
      !url.username &&
      !url.password &&
      host.includes(".") &&
      !/^(127\.|10\.|192\.168\.|169\.254\.|0\.|172\.(1[6-9]|2\d|3[01])\.)/.test(
        host,
      ) &&
      !/\.(local|localhost|internal)$/.test(host)
      ? url.href
      : null;
  } catch {
    return null;
  }
}

export function SearchImageGallery({ images }: { images: SearchImage[] }) {
  const valid = images
    .filter(
      (image) =>
        publicWebUrl(image.image_url) && publicWebUrl(image.source_url),
    )
    .slice(0, 3);
  if (!valid.length) return null;
  return (
    <section
      className="rafinha-search-images"
      aria-label="Imagens de referência da pesquisa"
    >
      <small>Imagens de referência · identificação ainda provável</small>
      <div>
        {valid.map((image) => (
          <a
            key={image.image_url}
            href={image.source_url}
            target="_blank"
            rel="noreferrer"
          >
            <img
              src={publicWebUrl(image.thumbnail_url || "") || image.image_url}
              alt={image.caption || "Referência da planta pesquisada"}
              loading="lazy"
              referrerPolicy="no-referrer"
              onError={(e) => {
                const original = publicWebUrl(image.image_url);
                if (original && e.currentTarget.src !== original) {
                  e.currentTarget.src = original;
                  return;
                }
                e.currentTarget.hidden = true;
              }}
            />
            <span>{image.domain || new URL(image.source_url).hostname}</span>
          </a>
        ))}
      </div>
    </section>
  );
}
