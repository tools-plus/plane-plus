/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useParams } from "next/navigation";
// plane imports
import { Tooltip } from "@plane/propel/tooltip";
import { EpicIcon } from "@plane/propel/icons";
import type { TIssue } from "@plane/types";
// hooks
import { useProject } from "@/hooks/store/use-project";
import { usePlatformOS } from "@/hooks/use-platform-os";

interface ParentChipProps {
  issue: TIssue;
}

const EPIC_STYLE: React.CSSProperties = {
  backgroundColor: "#fff7ed",
  color: "#d97706",
  borderRadius: "4px",
  padding: "1px 6px",
  fontSize: "11px",
  fontWeight: 500,
  display: "inline-flex",
  alignItems: "center",
  lineHeight: "18px",
  cursor: "pointer",
  border: "1px solid #fed7aa",
};

const PARENT_STYLE: React.CSSProperties = {
  backgroundColor: "#eff6ff",
  color: "#2563eb",
  borderRadius: "4px",
  padding: "1px 6px",
  fontSize: "11px",
  fontWeight: 500,
  display: "inline-flex",
  alignItems: "center",
  lineHeight: "18px",
  cursor: "pointer",
  border: "1px solid #bfdbfe",
};

export const ParentChip = observer(function ParentChip(props: ParentChipProps) {
  const { issue } = props;
  // router
  const { workspaceSlug: routerWorkspaceSlug } = useParams();
  const workspaceSlug = routerWorkspaceSlug?.toString();
  // hooks
  const { getProjectIdentifierById } = useProject();
  const { isMobile } = usePlatformOS();

  // early return if no parent
  if (!issue.parent_id) return null;

  // Use parent fields from API annotation (no store dependency)
  const parentSeqId = issue.parent__sequence_id;
  const parentProjectId = issue.parent__project_id;
  if (!parentSeqId || !parentProjectId) return null;

  const isEpicParent = !!issue.parent_is_epic;
  const parentProjectIdentifier = getProjectIdentifierById(parentProjectId);
  const parentIdentifier = `${parentProjectIdentifier}-${parentSeqId}`;

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
    if (workspaceSlug) {
      window.open(`/${workspaceSlug}/browse/${parentIdentifier}/`, "_self");
    }
  };

  return (
    <Tooltip tooltipContent={parentIdentifier} isMobile={isMobile} renderByDefault={false}>
      <button type="button" onClick={handleClick} style={isEpicParent ? EPIC_STYLE : PARENT_STYLE}>
        {isEpicParent && <EpicIcon className="size-3" />}
        {parentIdentifier}
      </button>
    </Tooltip>
  );
});
