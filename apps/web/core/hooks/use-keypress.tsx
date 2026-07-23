/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useRef } from "react";

const useKeypress = (key: string, callback: (event: KeyboardEvent) => void) => {
  // Every call site passes either an inline arrow or a handler defined in the
  // component body, so `callback` is a fresh reference on each render. Keeping
  // it in a ref lets the listener effect depend only on `key`, instead of
  // removing and re-adding a document-level keydown listener every render.
  const callbackRef = useRef(callback);

  useEffect(() => {
    callbackRef.current = callback;
  });

  useEffect(() => {
    const handleKeydown = (event: KeyboardEvent) => {
      if (event.key === key) {
        callbackRef.current(event);
      }
    };

    document.addEventListener("keydown", handleKeydown);

    return () => {
      document.removeEventListener("keydown", handleKeydown);
    };
  }, [key]);
};

export default useKeypress;
