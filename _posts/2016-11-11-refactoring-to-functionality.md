---
layout: post
---

# Refactoring towards Functionality

Yesterday, I refactored a method. 

Nothing unusual about that - we refactor code constantly. Code is, after all, better described as something grown than something built, and a large part of gardening is keeping the weeds in check. Normally, I wouldn't have given it a second thought.

What was unusual, though, was I was pairing with someone I hadn't paired with before, and she was relatively new to Java 8 constructs like Optionals. Pairing with someone new is always good for reflection.

As we went through the refactorings, I realised I was being motivated by a few simple pressures towards a functional approach. Each by themselves only made a small, incremental improvement, but composed together, they had a huge effect on the code.

Here's the original code:

```java
private Optional<ResponseWithMaybeDeal> matchResponseToDeal(BidResponse bidResponse) {
    Optional<String> dealIdFromResponse = getDealIdFromResponse(bidResponse);

    Optional<ResponseWithMaybeDeal> responseWithDeal1;
    if (dealIdFromResponse.isPresent()) {
        responseWithDeal1 = dealIdFromResponse
            .flatMap(dealId -> {
                Optional<UnrulySSPDeal> deal = findDeal(dealId);
                Optional<ResponseWithMaybeDeal> responseWithDeal;
                if (deal.isPresent()) {
                    responseWithDeal = Optional.of(new ResponseWithMaybeDeal(bidResponse, deal));
                } else {
                    responseWithDeal = Optional.empty();
                }
                return responseWithDeal;
            });
    } else {
        responseWithDeal1 = Optional.of(new ResponseWithMaybeDeal(bidResponse, Optional.empty()));
    }
    return responseWithDeal1;
}
```

This is taken from the auction logic in our ad exchange. When someone visits a page with an ad element, the browser sends us a request, which we then send off to various bidders: the winning bid determines the ad to display. Some of those bidders have arranged deals, which affects how we process their bids. 

The above method looks up the deal that applies to each bid, if there is one, and puts them into a composite object for further processing.

My first impression: well, I can trace through that and understand what's going on, but it's a little hairy. Let's see if we can smooth it out a bit.


### PRINCIPLE 1: Favour early-return over single-return.

The first thing I noticed was this:

```java
private Optional<ResponseWithMaybeDeal> matchResponseToDeal(BidResponse bidResponse) {
    Optional<String> dealIdFromResponse = getDealIdFromResponse(bidResponse);

    Optional<ResponseWithMaybeDeal> responseWithDeal1;
    if (dealIdFromResponse.isPresent()) {
        responseWithDeal1 = dealIdFromResponse
            .flatMap(dealId -> {
                Optional<UnrulySSPDeal> deal = findDeal(dealId);
                Optional<ResponseWithMaybeDeal> responseWithDeal;
                if (deal.isPresent()) {
                    responseWithDeal = Optional.of(new ResponseWithMaybeDeal(bidResponse, deal));
                } else {
                    responseWithDeal = Optional.empty();
                }
                return responseWithDeal;
            });
    } else {
        responseWithDeal1 = Optional.of(new ResponseWithMaybeDeal(bidResponse, Optional.empty()));
    }
    return responseWithDeal1;
}
```
Here we have two examples of the single-return style, one in the method itself and one in a lambda contained within the method. Arguments exist as to which of single-return and early-return style is more readable – personally, I find that tracking changes through mutable variables like this is harder to reason about than just returning values when you have them. Returning rather than assigning gives us:

```java
private Optional<ResponseWithMaybeDeal> matchResponseToDeal(BidResponse bidResponse) {
    Optional<String> dealIdFromResponse = getDealIdFromResponse(bidResponse);

    Optional<ResponseWithMaybeDeal> responseWithDeal1;
    if (dealIdFromResponse.isPresent()) {
        return dealIdFromResponse
            .flatMap(dealId -> {
                Optional<UnrulySSPDeal> deal = findDeal(dealId);
                Optional<ResponseWithMaybeDeal> responseWithDeal;
                if (deal.isPresent()) {
                    return Optional.of(new ResponseWithMaybeDeal(bidResponse, deal));
                } else {
                    return Optional.empty();
                }
                return responseWithDeal;
            });
    } else {
        return Optional.of(new ResponseWithMaybeDeal(bidResponse, Optional.empty()));
    }
    return responseWithDeal1;
}
```
That's reassuring, we have compile errors on the original return statements as they're unreachable, and the variables are unused. It's always nice when your IDE confirms that you've hit all the cases. Get rid of those lines and we get:

```java
private Optional<ResponseWithMaybeDeal> matchResponseToDeal(BidResponse bidResponse) {
    Optional<String> dealIdFromResponse = getDealIdFromResponse(bidResponse);

    if (dealIdFromResponse.isPresent()) {
        return dealIdFromResponse
            .flatMap(dealId -> {
                Optional<UnrulySSPDeal> deal = findDeal(dealId);
                if (deal.isPresent()) {
                    return Optional.of(new ResponseWithMaybeDeal(bidResponse, deal));
                } else {
                    return Optional.empty();
                }
            });
    } else {
        return Optional.of(new ResponseWithMaybeDeal(bidResponse, Optional.empty()));
    }
}
```
### PRINCIPLE 2: Favour if-expressions over if-statements

The next thing I noticed was this:

```java
private Optional<ResponseWithMaybeDeal> matchResponseToDeal(BidResponse bidResponse) {
    Optional<String> dealIdFromResponse = getDealIdFromResponse(bidResponse);

    if (dealIdFromResponse.isPresent()) {
        return dealIdFromResponse
            .flatMap(dealId -> {
                Optional<UnrulySSPDeal> deal = findDeal(dealId);
                if (deal.isPresent()) {
                    return Optional.of(new ResponseWithMaybeDeal(bidResponse, deal));
                } else {
                    return Optional.empty();
                }
            });
    } else {
        return Optional.of(new ResponseWithMaybeDeal(bidResponse, Optional.empty()));
    }
}
```
We have two `if` statements here, with both `if` and `else` clauses, each of which returns immediately. These can be replaced with `if`-expressions:

```java
private Optional<ResponseWithMaybeDeal> matchResponseToDeal(BidResponse bidResponse) {
    Optional<String> dealIdFromResponse = getDealIdFromResponse(bidResponse);

    return (dealIdFromResponse.isPresent()) 
        ? dealIdFromResponse
            .flatMap(dealId -> {
                Optional<UnrulySSPDeal> deal = findDeal(dealId);
                return deal.isPresent() 
                    ? Optional.of(new ResponseWithMaybeDeal(bidResponse, deal))
                    : Optional.empty();
            }) 
        : Optional.of(new ResponseWithMaybeDeal(bidResponse, Optional.empty()));
}
```
Is that clearer than the previous case? It's not helped by the syntax decay from keywords to ternary symbology. Writing code with ternaries is dangerous because it's easy to forget to structure code in an easily decomposable way.  Readability and aesthetics are always in the eye of the beholder, and are heavily influenced by experience with different paradigms.

We do end up with something that's slightly terser, but that's not the main point. This change *advertises something about the code*. More can happen in an `if`-statement than an `if`-expression: you can modify variables, call side-effecty `void` methods and so on. Making this an `if`-expression advertises that all we're doing is returning one of two things.

It's a more functional way of describing what the code's doing. It could be argued I'm making the code more functional, but really all I'm doing is exposing the functional properties of the code which already existed. Whether you think this is a good thing in and of itself is up to you, but – as you'll see – these changes make it easier to spot further functional refactorings down the line.

###PRINCIPLE 3: Don't treat Optionals like nulls

The next thing I noticed was:

```java
private Optional<ResponseWithMaybeDeal> matchResponseToDeal(BidResponse bidResponse) {
    Optional<String> dealIdFromResponse = getDealIdFromResponse(bidResponse);

    return (dealIdFromResponse.isPresent()) 
        ? dealIdFromResponse
            .flatMap(dealId -> {
                Optional<UnrulySSPDeal> deal = findDeal(dealId);
                return deal.isPresent() 
                    ? Optional.of(new ResponseWithMaybeDeal(bidResponse, deal))
                    : Optional.empty();
            }) 
        : Optional.of(new ResponseWithMaybeDeal(bidResponse, Optional.empty()));
}
```
`Optional`s are a really important addition to Java 8. Unfortunately, the general introduction to `Optional`s - that they're a better way of addressing the problems we get with `null` – tends to result in `Optional`-handling code looking like `null`-handling code at first. Our method is currently a good example of that.

`Optional`s don't just exist to represent the possibility of absence. Viewing them as that means you miss the real benefit: safety.

Safety, because `Optional`s provide methods which force you to address the absent case. `Optional` provides 3 ways of getting a `T` out of an `Optional<T>`: `Optional::orElse`, `Optional::orElseGet`, and `Optional::orElseThrow`.  Each of these requires you to describe the result you want when the thing you know might not be there turns out to not be there.

Technically, it also provides `Optional::get`, which allows you access to the Java 8 version of `NullPointerException`s if you really want them. This should be considered an alias to `Optional.orElseThrow(BadAtProgrammingException::new)`. 

The blue section here is easiest to refactor, from this:

```java
Optional<UnrulySSPDeal> deal = findDeal(dealId);
return deal.isPresent() 
    ? Optional.of(new ResponseWithMaybeDeal(bidResponse, deal))
    : Optional.empty();
```
To this:

```java
Optional<UnrulySSPDeal> deal = findDeal(dealId);
return deal.map(__ -> new ResponseWithMaybeDeal(bidResponse, deal));
```
This is a little awkward, because we're mapping over an `Optional` but not using its contents, which feels a little unnatural. An alternative implementation is this:

```java
Optional<UnrulySSPDeal> maybeDeal = findDeal(dealId);
return maybeDeal.map(deal -> new ResponseWithMaybeDeal(bidResponse, Optional.of(deal));
```
Here we're unwrapping and then re-wrapping the deal in an `Optional`. This does mean we can at least inline `findDeal` and the code won't break. So our whole method now looks like this:

```java
private Optional<ResponseWithMaybeDeal> matchResponseToDeal(BidResponse bidResponse) {
    Optional<String> dealIdFromResponse = getDealIdFromResponse(bidResponse);

    return (dealIdFromResponse.isPresent())
        ? dealIdFromResponse
            .flatMap(dealId -> 
                findDeal(dealId).map(deal -> new ResponseWithMaybeDeal(bidResponse, Optional.of(deal))))
        : Optional.of(new ResponseWithMaybeDeal(bidResponse, Optional.empty()));
}
```
The pink section is also easy to refactor, as we're already doing a mapping operation over it: we know if the deal isn't present, we'll have an `Optional.empty()`. So we can refactor this too:

```java
private Optional<ResponseWithMaybeDeal> matchResponseToDeal(BidResponse bidResponse) {
    Optional<String> dealIdFromResponse = getDealIdFromResponse(bidResponse);

    return dealIdFromResponse
        .flatMap(dealId -> 
            of(findDeal(dealId).map(deal -> new ResponseWithMaybeDeal(bidResponse, of(deal)))))
        .orElseGet(() -> of(new ResponseWithMaybeDeal(bidResponse, empty())));
}
```
There are a few important things to notice about this change:

* I've statically imported Optional.of and Optional.empty for the blogpost to prevent word wrap. I'm not a fan of statically importing Optional.of as the loss of context diminishes meaning. 
* I've used `orElseGet` with a lambda instead of just `orElse` with the value to prevent creating unnecessary objects. Generally, `orElseGet()` should be favoured over `orElse()` unless you already have an instance to return: in my opinion, little would be lost if the only way to get a `T` out of an `Optional<T>` was `orElseGet()`.
* In order to use `Optional`'s branching, we have to wrap our return values in more `Optional`s.

### PRINCIPLE 4: Think outside the box

At this point we started asking ourselves: this wrapping in `Optional`s is clunky, why are we doing that? We're doing that in order to return an `Optional<ResponseWithMaybeDeal>`, because we're in a situation where we can return `Optional.empty()`. Where's the empty case?

Because of the way we're composing nested optionals, it's difficult to spot in this version of the code, compared to the original. The empty case is when we have a deal id on a response, but we can't find a matching deal. So we're doing two things in this method: augmenting with the deal, and filtering out invalid deal ids.

Functions should do one thing.

So, we changed what the function does, and moved the filtering outside. If we just pair the response to the corresponding deal (when we can find one), we no longer have a reason to wrap in an `Optional`, allowing us to go from this:

```java
private Optional<ResponseWithMaybeDeal> matchResponseToDeal(BidResponse bidResponse) {
    Optional<String> dealIdFromResponse = getDealIdFromResponse(bidResponse);

    return dealIdFromResponse
        .flatMap(dealId -> 
            of(maybeDeal.map(deal -> new ResponseWithMaybeDeal(bidResponse, of(deal))));
        })
        .orElseGet(() -> of(new ResponseWithMaybeDeal(bidResponse, empty())));
}
```
To this:

```java
private ResponseWithMaybeDeal matchResponseToDeal(BidResponse bidResponse) {
    Optional<String> dealIdFromResponse = getDealIdFromResponse(bidResponse);

    return dealIdFromResponse
        .flatMap(dealId -> 
            findDeal(dealId).map(deal -> new ResponseWithMaybeDeal(bidResponse, Optional.of(deal))))
        .orElseGet(() -> new ResponseWithMaybeDeal(bidResponse, Optional.empty()));
}
```
We could have made this simplification without having gone through the previous steps, but the path we were going down led us to question whether or not we were doing the right thing.

### PRINCIPLE 5: Repeated patterns are usually liftable

The next thing I noticed was:

```java
private ResponseWithMaybeDeal matchResponseToDeal(BidResponse bidResponse) {
    Optional<String> dealIdFromResponse = getDealIdFromResponse(bidResponse);

    return dealIdFromResponse
        .flatMap(dealId -> 
            findDeal(dealId).map(deal -> new ResponseWithMaybeDeal(bidResponse, Optional.of(deal))))
        .orElseGet(() -> new ResponseWithMaybeDeal(bidResponse, Optional.empty()));
}
```
We're returning a ResponseWithMaybeDeal from this method, and we're creating it on both paths. So we can simplify that by lifting that part out – first by extracting the return value into a variable:

```java
private ResponseWithMaybeDeal matchResponseToDeal(BidResponse bidResponse) {
    Optional<String> dealIdFromResponse = getDealIdFromResponse(bidResponse);

    ResponseWithMaybeDeal responseWithMaybeDeal = dealIdFromResponse
        .flatMap(dealId -> findDeal(dealId).map(deal -> new ResponseWithMaybeDeal(bidResponse, Optional.of(deal))))
        .orElseGet(() -> new ResponseWithMaybeDeal(bidResponse, Optional.empty()));
    
    return responseWithMaybeDeal;
}
```
And then pulling the construction up to the top level: 

```java
private ResponseWithMaybeDeal matchResponseToDeal(BidResponse bidResponse) {
    Optional<String> dealIdFromResponse = getDealIdFromResponse(bidResponse);

    Optional<UnrulySSPDeal> maybeDeal = dealIdFromResponse
        .flatMap(dealId -> findDeal(dealId).map(deal -> Optional.of(deal)))
        .orElseGet(() -> Optional.empty());

    return new ResponseWithMaybeDeal(bidResponse, maybeDeal);
}
```
We're nearly done here, because even when that's done, the pink code stuck out. We're mapping an Optional to wrap its contents in another Optional, then taking it out, or otherwise returning empty? What does that even mean? 

Turns out, it means exactly the same as:

```java
private ResponseWithMaybeDeal matchResponseToDeal(BidResponse bidResponse) {
    Optional<String> dealIdFromResponse = getDealIdFromResponse(bidResponse);

    Optional<UnrulySSPDeal> maybeDeal = dealIdFromResponse
        .flatMap(dealId -> findDeal(dealId));

    return new ResponseWithMaybeDeal(bidResponse, maybeDeal);
}
```
Which can then be inlined and method-reference-extracted to:

```java
private ResponseWithMaybeDeal matchResponseToDeal(BidResponse bidResponse) {
    Optional<UnrulySSPDeal> maybeDeal = getDealIdFromResponse(bidResponse).flatMap(this::findDeal);
    return new ResponseWithMaybeDeal(bidResponse, maybeDeal);
}
```
And, finally it feels like we're done. First get a `maybeDeal` (by getting the deal id, and then looking up the deal, assuming they both exist), and then we construct a `ResponseWithMaybeDeal` with the `BidResponse` and the `maybeDeal`. It really does just do what it says on the tin.

### SUMMING UP

Before we go, let's just reflect on how far we came - we started with this:

```java
private Optional<ResponseWithMaybeDeal> matchResponseToDeal(BidResponse bidResponse) {
    Optional<String> dealIdFromResponse = getDealIdFromResponse(bidResponse);

    Optional<ResponseWithMaybeDeal> responseWithDeal1;
    if (dealIdFromResponse.isPresent()) {
        responseWithDeal1 = dealIdFromResponse
            .flatMap(dealId -> {
                Optional<UnrulySSPDeal> deal = findDeal(dealId);
                Optional<ResponseWithMaybeDeal> responseWithDeal;
                if (deal.isPresent()) {
                    responseWithDeal = Optional.of(new ResponseWithMaybeDeal(bidResponse, deal));
                } else {
                    responseWithDeal = Optional.empty();
                }
                return responseWithDeal;
            });
    } else {
        responseWithDeal1 = Optional.of(new ResponseWithMaybeDeal(bidResponse, Optional.empty()));
    }
    return responseWithDeal1;
}
```
And ended up with this:

```java
private ResponseWithMaybeDeal matchResponseToDeal(BidResponse bidResponse) {
    Optional<UnrulySSPDeal> maybeDeal = getDealIdFromResponse(bidResponse).flatMap(this::findDeal);
    return new ResponseWithMaybeDeal(bidResponse, maybeDeal);
}
```
Seems pretty good.
