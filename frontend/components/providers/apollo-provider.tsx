"use client";

import { HttpLink } from "@apollo/client";
import {
  ApolloClient,
  ApolloNextAppProvider,
  InMemoryCache,
} from "@apollo/client-integration-nextjs";

const graphqlUrl =
  process.env.NEXT_PUBLIC_GRAPHQL_URL ?? "http://localhost:8000/graphql";

function makeClient() {
  return new ApolloClient({
    cache: new InMemoryCache(),
    link: new HttpLink({
      uri: graphqlUrl,
    }),
  });
}

export function ApolloProvider({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <ApolloNextAppProvider makeClient={makeClient}>
      {children}
    </ApolloNextAppProvider>
  );
}
