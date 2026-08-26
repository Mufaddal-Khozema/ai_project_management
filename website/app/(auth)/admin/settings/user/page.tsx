"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { useState, useEffect } from "react";
import { useCurrentUser, useUpdateProfileMutation } from "@/lib/api";
import {
  UserCircle,
  Bell,
  Shield,
  KeyRound,
  Palette,
  Check,
  Mail,
  Save,
} from "lucide-react";

export default function UserSettingsPage() {
  const { data: user, isLoading } = useCurrentUser();
  const updateProfile = useUpdateProfileMutation();

  const [displayName, setDisplayName] = useState("");
  const [avatarUrl, setAvatarUrl] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (user) {
      setDisplayName(user.name ?? "");
      setAvatarUrl(user.avatar ?? "");
    }
  }, [user]);

  const handleSaveProfile = async () => {
    try {
      await updateProfile.mutateAsync({
        body: {
          name: displayName || null,
          avatar: avatarUrl || null,
        },
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {}
  };

  return (
    <>
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-card-foreground">
          User settings
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Manage your profile, security, and preferences
        </p>
      </div>

      <div className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <UserCircle size={14} />
              Public profile
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            {isLoading ? (
              <div className="space-y-4">
                <div className="h-16 w-16 rounded-full bg-muted animate-pulse" />
                <div className="h-10 rounded-lg bg-muted animate-pulse" />
                <div className="h-10 rounded-lg bg-muted animate-pulse" />
              </div>
            ) : (
              <>
                <div className="flex items-center gap-4">
                  <div className="flex h-16 w-16 items-center justify-center overflow-hidden rounded-full bg-gradient-to-br from-primary to-[#4f46e5] text-lg font-semibold text-primary-foreground">
                    {avatarUrl ? (
                      <img src={avatarUrl} alt="" className="size-full object-cover" />
                    ) : (
                      user?.name?.[0]?.toUpperCase() ?? user?.email?.[0]?.toUpperCase() ?? "?"
                    )}
                  </div>
                  <div>
                    <Button variant="outline" size="sm">
                      Change avatar
                    </Button>
                    <p className="mt-1 text-[11px] text-muted-foreground">
                      Paste an image URL below
                    </p>
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="text-xs font-medium text-muted-foreground">
                    Avatar URL
                  </label>
                  <Input
                    value={avatarUrl}
                    onChange={(e) => setAvatarUrl(e.target.value)}
                    placeholder="https://example.com/avatar.jpg"
                  />
                </div>

                <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
                  <div className="space-y-2">
                    <label className="text-xs font-medium text-muted-foreground">
                      Display name
                    </label>
                    <Input
                      value={displayName}
                      onChange={(e) => setDisplayName(e.target.value)}
                      placeholder="Your name"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-xs font-medium text-muted-foreground">
                      Email
                    </label>
                    <div className="relative">
                      <Mail
                        size={14}
                        className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
                      />
                      <Input value={user?.email ?? ""} className="pl-9" disabled />
                    </div>
                  </div>
                </div>

                <div className="flex justify-end">
                  <Button
                    size="sm"
                    onClick={handleSaveProfile}
                    disabled={updateProfile.isPending}
                  >
                    {updateProfile.isPending ? (
                      <span className="size-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                    ) : saved ? (
                      <>
                        <Check size={14} className="mr-1" /> Saved
                      </>
                    ) : (
                      <>
                        <Save size={14} className="mr-1" /> Save profile
                      </>
                    )}
                  </Button>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield size={14} />
              Security
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between rounded-lg border border-border bg-muted p-4">
              <div className="flex items-center gap-3">
                <KeyRound size={16} className="text-muted-foreground" />
                <div>
                  <p className="text-sm font-medium text-card-foreground">
                    Password
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Last changed 3 months ago
                  </p>
                </div>
              </div>
              <Button variant="outline" size="sm">
                Change
              </Button>
            </div>

            <div className="flex items-center justify-between rounded-lg border border-border bg-muted p-4">
              <div className="flex items-center gap-3">
                <Shield size={16} className="text-muted-foreground" />
                <div>
                  <p className="text-sm font-medium text-card-foreground">
                    Two-factor auth
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Enabled via authenticator app
                  </p>
                </div>
              </div>
              <Badge variant="outline">Active</Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Palette size={14} />
              Preferences
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Palette size={16} className="text-muted-foreground" />
                <div>
                  <p className="text-sm font-medium text-card-foreground">
                    Theme
                  </p>
                  <p className="text-xs text-muted-foreground">
                    System preference
                  </p>
                </div>
              </div>
              <Select defaultValue="system">
                <SelectTrigger className="w-32">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="dark">Dark</SelectItem>
                  <SelectItem value="light">Light</SelectItem>
                  <SelectItem value="system">System</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Bell size={16} className="text-muted-foreground" />
                <div>
                  <p className="text-sm font-medium text-card-foreground">
                    Notifications
                  </p>
                  <p className="text-xs text-muted-foreground">
                    In-app and push
                  </p>
                </div>
              </div>
              <div className="flex h-6 w-11 cursor-pointer items-center rounded-full bg-primary px-0.5 transition-colors">
                <div className="h-5 w-5 translate-x-5 rounded-full bg-white shadow-sm" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </>
  );
}