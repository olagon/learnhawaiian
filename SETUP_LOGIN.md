# Enabling cross-device sync (Supabase setup)

The login system is already wired into the app. It stays hidden until you fill in two values from a free Supabase project. Once those are filled in, a sign-in button appears in the header and users can opt in to sync their progress across devices.

This whole setup takes about 15 minutes and costs nothing.

## What you're getting

A working magic-link sign-in flow. Users enter their email, get a one-time link, click it, and land back on the app signed in. Their progress then syncs after every round. They can sign out and the app still works locally. No passwords, no Google or Apple sign-in flow to configure (those can be added later).

## Step 1. Create a Supabase project

Go to https://supabase.com and sign up with your GitHub account. Once you're in, click **New project**. Pick any name (`olelodaily` works), pick a strong database password (save it somewhere, you probably won't need it again), pick the region closest to you. Wait about a minute for provisioning.

## Step 2. Create the progress table

In your Supabase dashboard, click **SQL Editor** in the left sidebar, then **New query**. Paste this and click **Run**.

```sql
create table progress (
  user_id uuid references auth.users primary key,
  data jsonb not null,
  updated_at timestamptz default now()
);

alter table progress enable row level security;

create policy "users read own progress"
  on progress for select
  using (auth.uid() = user_id);

create policy "users insert own progress"
  on progress for insert
  with check (auth.uid() = user_id);

create policy "users update own progress"
  on progress for update
  using (auth.uid() = user_id);
```

The Row Level Security policies are what guarantee that even though every user's app talks to the same database with the same public key, each user can only read and write their own row. No one can access anyone else's progress.

## Step 3. Configure auth

In the Supabase dashboard, go to **Authentication → URL Configuration** in the left sidebar.

Set **Site URL** to:

```
https://olelodaily.com
```

Under **Redirect URLs**, add both of these (one per line):

```
https://olelodaily.com
https://olelodaily.com/
```

This tells Supabase that magic links should redirect users back to your app, not somewhere else.

## Step 4. Get your project keys

Go to **Project Settings → API** in the left sidebar. You'll see two values you need.

**Project URL.** Looks like `https://xxxxxxxxxxxx.supabase.co`. Copy it.

**Project API key, anon (public).** A long string. Copy it. This key is safe to put in client-side code because Row Level Security restricts what it can do per user.

## Step 5. Paste into index.html

Open `index.html` and find this block near the bottom:

```js
const SUPABASE_URL = '';
const SUPABASE_ANON_KEY = '';
```

Paste your values between the quotes:

```js
const SUPABASE_URL = 'https://xxxxxxxxxxxx.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOi...long-string...';
```

Save the file.

## Step 6. Push and test

```bash
cd /Library/WebServer/Documents/learnhawaiian
git add index.html
git commit -m "Enable cloud sync"
git push
```

Wait a minute for GitHub Pages to redeploy. Visit https://olelodaily.com. You should see a new circle icon in the header. Click it, enter your email, check your inbox, click the magic link, you'll land back on the app signed in.

Do a round, then open the same site in a different browser (or your phone). Sign in with the same email there. Your progress should appear.

## How it handles conflicts

The merge logic is built into the app. Two safety rules:

**Mastered words are sticky.** Once you've gotten a word to level 5 on any device, it stays at level 5 unless you actively miss it elsewhere afterward. You can't lose mastered words by signing in.

**For everything else, the more recent attempt wins.** Each progress entry carries a timestamp. When merging, whichever device touched the word more recently is treated as the source of truth.

The first time someone signs in on a device that already has local progress, the app shows them a preview of what's about to happen ("This device has 47 mastered words, your account has 130, after combining you'll have 142") and they confirm before any merge runs.

## Free tier limits (you won't hit these)

Supabase free tier covers:
- 50,000 monthly active users
- 500MB database
- 5GB bandwidth per month
- Unlimited API requests

Each user's progress row is a few KB at most. You'd need tens of thousands of active users before storage becomes a concern. Even then, the paid tier is $25/month and only kicks in if you cross those limits.

## If you ever want to add Google or Apple sign-in

In the Supabase dashboard, **Authentication → Providers**. Enable the provider, paste in OAuth credentials from Google Cloud Console or Apple Developer portal. The auth flow in the app already handles all sign-in providers Supabase offers, but you'd want to add a button in `authBodySignedOut` to trigger the OAuth flow. Tell me when you're ready and I'll wire it up.

## If something goes wrong

The most common issue is the magic link redirecting to the wrong URL. Check **Authentication → URL Configuration** in Supabase and make sure Site URL and Redirect URLs both contain the exact domain you're hosting at, with `https://`.

Second most common: forgetting to push the updated `index.html` to GitHub. The local site might work but the live site won't show the auth button until the deploy finishes.

Open the browser console on the live site (Cmd-Option-J on Mac) and look for errors. The Supabase SDK logs problems clearly.
