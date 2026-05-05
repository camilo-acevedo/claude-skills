/**
 * JWT validation and middleware.
 */

export const JWT_ALGO = "HS256";

export interface Claims {
    sub: string;
    exp: number;
}

export function verifyJwt(token: string): Claims {
    return { sub: "x", exp: 0 };
}

export class AuthMiddleware {
    constructor(public secret: string) {}
}

export default function init(): void {}
