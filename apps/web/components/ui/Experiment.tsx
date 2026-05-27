"use client";

/**
 * 简单 A/B 包装组件。
 *
 * 用法:
 *   <Experiment flag={FLAGS.PRICING_19_VS_29} variants={{
 *     control: <Pricing price={19} />,
 *     b: <Pricing price={29} />,
 *   }} />
 *
 * 在用户首次见到 variant 时 emit "experiment.viewed" 事件,
 * 便于 PostHog 上算转化漏斗。
 */

import { useEffect, useState } from "react";
import { variant as readVariant } from "@/lib/flags";
import { track } from "@/lib/analytics";

type Props = {
  flag: string;
  variants: Record<string, React.ReactNode>;
  fallback?: string;
};

export function Experiment({ flag, variants, fallback = "control" }: Props) {
  const [v, setV] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    readVariant(flag, fallback).then((value) => {
      if (cancelled) return;
      setV(value);
      track("experiment.viewed", { flag, variant: value });
    });
    return () => { cancelled = true; };
  }, [flag, fallback]);

  if (v === null) return variants[fallback] ?? null;        // 加载时显示默认
  return variants[v] ?? variants[fallback] ?? null;
}
