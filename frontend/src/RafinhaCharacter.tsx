import { useEffect, useRef, useState } from "react";
import {
  EXPRESSION_LABELS,
  RAF_EXPRESSIONS,
  expressionAsset,
  type RafinhaExpression,
} from "./rafinhaExpressions";

export function RafinhaCharacter({
  expression,
  motion,
}: {
  expression: string;
  motion: boolean;
}) {
  const source = expressionAsset(expression);
  const old = useRef(source);
  const [previous, setPrevious] = useState<string | null>(null);
  useEffect(() => {
    if (old.current === source) return;
    setPrevious(motion ? old.current : null);
    old.current = source;
    const timer = setTimeout(() => setPrevious(null), 260);
    return () => clearTimeout(timer);
  }, [source, motion]);
  const name = RAF_EXPRESSIONS[expression as RafinhaExpression] || "greeting";
  return (
    <div className="rafinha-character-frame" data-expression={name}>
      {previous && (
        <img
          className="rafinha-character-previous"
          src={previous}
          alt=""
          aria-hidden="true"
        />
      )}
      <img
        className="rafinha-character"
        key={source}
        src={source}
        alt={`Rafinha ${EXPRESSION_LABELS[name]}`}
      />
    </div>
  );
}
