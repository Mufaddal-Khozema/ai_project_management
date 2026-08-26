"use client";

import { useRouter } from "next/navigation";
import { Settings, LogOut } from "lucide-react";
import { useCurrentUser } from "@/lib/api";
import { StorageKeys } from "@/constants";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuGroup,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";

function getInitials(name: string | null | undefined, email: string): string {
  if (name) {
    return name
      .split(" ")
      .map((n) => n[0])
      .join("")
      .toUpperCase()
      .slice(0, 2);
  }
  return email[0].toUpperCase();
}

export function UserMenu() {
  const { data: user, isLoading } = useCurrentUser();
  const router = useRouter();

  const handleLogout = () => {
    localStorage.removeItem(StorageKeys.TOKEN);
    router.replace("/signup");
  };

  const handleSettings = () => {
    router.push("/admin/settings/user");
  };

  if (isLoading || !user) {
    return (
      <div className="size-8 rounded-full bg-muted animate-pulse" />
    );
  }

  const initials = getInitials(user.name, user.email);
  const avatarUrl = user.avatar;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger className="size-10 overflow-hidden rounded-full border border-border bg-muted text-xs font-medium text-card-foreground hover:ring-2 hover:ring-ring transition-shadow outline-none focus-visible:ring-2 focus-visible:ring-ring">
        <Avatar size="lg">
          {avatarUrl ? (
            <AvatarImage src={avatarUrl} alt="" />
          ) : null}
          <AvatarFallback>{initials}</AvatarFallback>
        </Avatar>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        <DropdownMenuGroup>
          <DropdownMenuLabel className="font-normal">
            <p className="truncate text-sm font-medium text-foreground">
              {user.name ?? "User"}
            </p>
            <p className="truncate text-xs text-muted-foreground">
              {user.email}
            </p>
          </DropdownMenuLabel>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={handleSettings}>
          <Settings size={15} />
          Settings
        </DropdownMenuItem>
        <DropdownMenuItem
          variant="destructive"
          onClick={handleLogout}
        >
          <LogOut size={15} />
          Logout
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
