/// <reference types="vite/client" />

declare interface ImportMetaEnv {
	readonly VITE_GOOGLE_CLIENT_ID: string;
	readonly VITE_API_URL: string;
}

declare interface ImportMeta {
	readonly env: ImportMetaEnv;
}
