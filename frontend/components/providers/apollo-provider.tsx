"use client";

import { ApolloLink, HttpLink } from "@apollo/client";
import { CombinedGraphQLErrors } from "@apollo/client/errors";
import { ErrorLink } from "@apollo/client/link/error";
import {
  ApolloClient,
  ApolloNextAppProvider,
  InMemoryCache,
} from "@apollo/client-integration-nextjs";

import { UNAUTHENTICATED_EVENT } from "@/lib/auth";
import { graphqlUrl } from "@/lib/graphql/config";

const authErrorLink = new ErrorLink(({ error }) => {
  if (
    typeof window !== "undefined" &&
    CombinedGraphQLErrors.is(error) &&
    error.errors.some((item) => item.extensions?.code === "UNAUTHENTICATED")
  ) {
    window.dispatchEvent(new Event(UNAUTHENTICATED_EVENT));
  }
});

function makeClient() {
  return new ApolloClient({
    cache: new InMemoryCache(),
    link: ApolloLink.from([
      authErrorLink,
      new HttpLink({
        uri: graphqlUrl,
        // Sends the HTTP-only session cookie set by the API's /auth endpoints.
        credentials: "include",
      }),
    ]),
  });
}

export function ApolloProvider({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <ApolloNextAppProvider makeClient={makeClient}>
      {children}
    </ApolloNextAppProvider>
  );
}
