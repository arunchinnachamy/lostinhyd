import { defineMiddleware } from 'astro:middleware';

// Cache durations (in seconds)
const CACHE_DURATIONS = {
  'homepage': 300,        // 5 minutes for homepage
  'events-list': 600,     // 10 minutes for events list
  'event-detail': 1800,   // 30 minutes for event detail pages
  'categories': 3600,     // 1 hour for category pages
  'static': 86400,        // 24 hours for static assets
};

export const onRequest = defineMiddleware(async (context, next) => {
  const url = new URL(context.request.url);
  const pathname = url.pathname;
  
  // Determine cache duration based on path
  let maxAge = CACHE_DURATIONS['static'];
  let staleWhileRevalidate = 3600; // 1 hour stale-while-revalidate
  
  if (pathname === '/' || pathname === '/index.html') {
    maxAge = CACHE_DURATIONS['homepage'];
    staleWhileRevalidate = 300;
  } else if (pathname.startsWith('/events/')) {
    if (pathname === '/events/' || pathname === '/events/index.html') {
      maxAge = CACHE_DURATIONS['events-list'];
    } else {
      maxAge = CACHE_DURATIONS['event-detail'];
    }
  } else if (pathname.startsWith('/category/')) {
    maxAge = CACHE_DURATIONS['categories'];
  }
  
  // Process the request
  const response = await next();
  
  // Clone response to add headers
  const newResponse = new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: response.headers
  });
  
  // Add cache headers
  newResponse.headers.set('Cache-Control', `public, max-age=${maxAge}, stale-while-revalidate=${staleWhileRevalidate}`);
  newResponse.headers.set('Vary', 'Accept-Encoding');
  
  // Add debugging info in development
  if (import.meta.env.DEV) {
    newResponse.headers.set('X-Cache-TTL', maxAge.toString());
  }
  
  return newResponse;
});
